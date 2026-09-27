use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, UNIX_EPOCH};
use tauri::{AppHandle, Emitter, Manager, State};

const MAX_LINE_BYTES: usize = 2 * 1024 * 1024;
const MAX_PREVIEW_BYTES: u64 = 8 * 1024 * 1024;
const MAX_TEXT_CHARS: usize = 200_000;
const MAX_ARTIFACTS: usize = 200;

struct AppState {
    root: Mutex<Result<PathBuf, String>>,
    starting: Mutex<bool>,
    stdin: Mutex<Option<ChildStdin>>,
    child: Mutex<Option<Child>>,
}

#[derive(Serialize)]
struct HarnessInfo {
    root: Option<String>,
    running: bool,
    error: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Artifact {
    name: String,
    bytes: u64,
    modified_ms: u64,
    kind: String,
}

#[derive(Serialize)]
struct ArtifactBody {
    name: String,
    kind: String,
    mime: String,
    truncated: bool,
    text: Option<String>,
    base64: Option<String>,
}

fn is_harness(path: &Path) -> bool {
    path.join("bin/pi").is_file() && path.join("extensions/load-skills.ts").is_file()
}

fn find_repo_root() -> Result<PathBuf, String> {
    if let Ok(from_env) = std::env::var("DECODER_PI_ROOT") {
        let path = PathBuf::from(&from_env);
        if is_harness(&path) {
            return Ok(path);
        }
        return Err(format!(
            "DECODER_PI_ROOT is not a decoder-pi checkout: {from_env}"
        ));
    }

    let mut starts = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        starts.push(cwd);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            starts.push(parent.to_path_buf());
        }
    }

    for start in starts {
        let mut current = start;
        loop {
            if is_harness(&current) {
                return Ok(current);
            }
            if !current.pop() {
                break;
            }
        }
    }

    Err(
        "could not find decoder-pi (bin/pi and extensions/load-skills.ts). Set DECODER_PI_ROOT."
            .into(),
    )
}

/// Split a stdout buffer on LF only. Unicode line separators stay inside JSON strings.
fn drain_lines(buf: &mut Vec<u8>) -> Vec<Vec<u8>> {
    let mut lines = Vec::new();
    while let Some(pos) = buf.iter().position(|byte| *byte == b'\n') {
        let mut line: Vec<u8> = buf.drain(..=pos).collect();
        line.pop();
        if line.last() == Some(&b'\r') {
            line.pop();
        }
        if !line.is_empty() {
            lines.push(line);
        }
    }
    lines
}

fn read_stdout(app: AppHandle, mut stdout: impl Read) {
    let mut carry = Vec::new();
    let mut chunk = [0u8; 8192];
    loop {
        match stdout.read(&mut chunk) {
            Ok(0) => break,
            Ok(n) => {
                carry.extend_from_slice(&chunk[..n]);
                if carry.len() > MAX_LINE_BYTES && !carry.contains(&b'\n') {
                    carry.clear();
                    let _ = app.emit(
                        "pi-stderr",
                        "dropped an oversized Pi stdout record".to_string(),
                    );
                    continue;
                }
                for line in drain_lines(&mut carry) {
                    match std::str::from_utf8(&line) {
                        Ok(text) => match serde_json::from_str::<Value>(text) {
                            Ok(value) => {
                                let _ = app.emit("pi-event", value);
                            }
                            Err(err) => {
                                let _ =
                                    app.emit("pi-stderr", format!("Pi stdout was not JSON: {err}"));
                            }
                        },
                        Err(_) => {
                            let _ =
                                app.emit("pi-stderr", "Pi stdout line was not UTF-8".to_string());
                        }
                    }
                }
            }
            Err(err) => {
                let _ = app.emit("pi-stderr", format!("reading Pi stdout failed: {err}"));
                break;
            }
        }
    }
    let _ = app.emit("pi-exit", "Pi stdout closed".to_string());
}

fn read_stderr(app: AppHandle, mut stderr: impl Read) {
    let mut carry = Vec::new();
    let mut chunk = [0u8; 4096];
    loop {
        match stderr.read(&mut chunk) {
            Ok(0) => break,
            Ok(n) => {
                carry.extend_from_slice(&chunk[..n]);
                for line in drain_lines(&mut carry) {
                    let text = String::from_utf8_lossy(&line).trim().to_string();
                    if !text.is_empty() {
                        let _ = app.emit("pi-stderr", text);
                    }
                }
            }
            Err(err) => {
                let _ = app.emit("pi-stderr", format!("reading Pi stderr failed: {err}"));
                break;
            }
        }
    }
}

fn spawn_pi(
    app: &AppHandle,
    root: &Path,
    stdin_slot: &Mutex<Option<ChildStdin>>,
    child_slot: &Mutex<Option<Child>>,
) -> Result<(), String> {
    let mut child = Command::new(root.join("bin/pi"))
        .arg("--mode")
        .arg("rpc")
        .current_dir(root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("failed to start {}: {err}", root.join("bin/pi").display()))?;

    let stdin = child.stdin.take().ok_or("Pi did not provide stdin")?;
    let stdout = child.stdout.take().ok_or("Pi did not provide stdout")?;
    let stderr = child.stderr.take().ok_or("Pi did not provide stderr")?;

    let app_out = app.clone();
    thread::spawn(move || read_stdout(app_out, stdout));
    let app_err = app.clone();
    thread::spawn(move || read_stderr(app_err, stderr));

    *stdin_slot.lock().map_err(|_| "Pi stdin lock poisoned")? = Some(stdin);
    *child_slot.lock().map_err(|_| "Pi process lock poisoned")? = Some(child);
    Ok(())
}

fn shutdown(state: &AppState) {
    if let Ok(mut stdin) = state.stdin.lock() {
        drop(stdin.take());
    }
    let Ok(mut child_slot) = state.child.lock() else {
        return;
    };
    let Some(mut child) = child_slot.take() else {
        return;
    };
    let started = Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if started.elapsed() < Duration::from_secs(3) => {
                thread::sleep(Duration::from_millis(50));
            }
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                break;
            }
        }
    }
}

fn harness_info(state: &AppState) -> HarnessInfo {
    let root = state.root.lock().ok();
    let (root, error) = match root.as_ref().map(|result| result.as_ref()) {
        Some(Ok(path)) => (Some(path.display().to_string()), None),
        Some(Err(err)) => (None, Some(err.clone())),
        None => (None, Some("harness state lock poisoned".into())),
    };
    let running = state.child.lock().ok().is_some_and(|child| child.is_some());
    HarnessInfo {
        root,
        running,
        error,
    }
}

#[tauri::command]
fn start_harness(app: AppHandle, state: State<AppState>) -> Result<HarnessInfo, String> {
    let root = state
        .root
        .lock()
        .map_err(|_| "harness state lock poisoned")?
        .clone()?;
    {
        let mut starting = state
            .starting
            .lock()
            .map_err(|_| "harness state lock poisoned")?;
        let child = state.child.lock().map_err(|_| "Pi process lock poisoned")?;
        if *starting || child.is_some() {
            return Ok(harness_info(&state));
        }
        *starting = true;
    }
    if let Err(err) = spawn_pi(&app, &root, &state.stdin, &state.child) {
        if let Ok(mut starting) = state.starting.lock() {
            *starting = false;
        }
        return Err(err);
    }
    Ok(harness_info(&state))
}

#[tauri::command]
fn pi_send(state: State<AppState>, message: Value) -> Result<(), String> {
    let line = serde_json::to_string(&message).map_err(|err| err.to_string())?;
    let mut stdin = state.stdin.lock().map_err(|_| "Pi stdin lock poisoned")?;
    let stdin = stdin.as_mut().ok_or("Pi is not running")?;
    stdin
        .write_all(line.as_bytes())
        .and_then(|_| stdin.write_all(b"\n"))
        .and_then(|_| stdin.flush())
        .map_err(|err| format!("failed to write to Pi: {err}"))
}

fn kind_for(path: &Path) -> Option<&'static str> {
    match path
        .extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| ext.to_ascii_lowercase())
        .as_deref()
    {
        Some("png") => Some("png"),
        Some("jpg" | "jpeg") => Some("jpeg"),
        Some("html" | "htm") => Some("html"),
        Some("csv") => Some("csv"),
        Some("json") => Some("json"),
        Some("md") => Some("md"),
        _ => None,
    }
}

fn collect_artifacts(runs: &Path, dir: &Path, out: &mut Vec<Artifact>) -> Result<(), String> {
    if out.len() >= MAX_ARTIFACTS {
        return Ok(());
    }
    let entries = fs::read_dir(dir).map_err(|err| format!("reading {}: {err}", dir.display()))?;
    for entry in entries {
        if out.len() >= MAX_ARTIFACTS {
            break;
        }
        let entry = entry.map_err(|err| err.to_string())?;
        let path = entry.path();
        if path.is_dir() {
            collect_artifacts(runs, &path, out)?;
            continue;
        }
        let Some(kind) = kind_for(&path) else {
            continue;
        };
        let meta = entry.metadata().map_err(|err| err.to_string())?;
        let name = path
            .strip_prefix(runs)
            .map_err(|err| err.to_string())?
            .components()
            .map(|component| component.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");
        let modified_ms = meta
            .modified()
            .ok()
            .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
            .map(|duration| duration.as_millis() as u64)
            .unwrap_or(0);
        out.push(Artifact {
            name,
            bytes: meta.len(),
            modified_ms,
            kind: kind.to_string(),
        });
    }
    Ok(())
}

#[tauri::command]
fn list_artifacts(state: State<AppState>) -> Result<Vec<Artifact>, String> {
    let root = state
        .root
        .lock()
        .map_err(|_| "harness state lock poisoned")?
        .clone()?;
    let runs = root.join("runs");
    if !runs.is_dir() {
        return Ok(Vec::new());
    }
    let mut artifacts = Vec::new();
    collect_artifacts(&runs, &runs, &mut artifacts)?;
    artifacts.sort_by(|a, b| b.modified_ms.cmp(&a.modified_ms).then(a.name.cmp(&b.name)));
    Ok(artifacts)
}

fn artifact_path(root: &Path, relative: &str) -> Result<PathBuf, String> {
    if relative.is_empty()
        || relative.contains('\0')
        || relative.starts_with('/')
        || relative.starts_with('\\')
        || relative
            .split(['/', '\\'])
            .any(|part| part == ".." || part.is_empty())
    {
        return Err("path is outside runs/".into());
    }
    let runs = root
        .join("runs")
        .canonicalize()
        .map_err(|err| format!("runs/ is not available: {err}"))?;
    let candidate = runs.join(relative);
    let canon = candidate
        .canonicalize()
        .map_err(|_| "file is not in runs/".to_string())?;
    if !canon.starts_with(&runs) {
        return Err("path is outside runs/".into());
    }
    Ok(canon)
}

fn mime_for(kind: &str) -> &'static str {
    match kind {
        "png" => "image/png",
        "jpeg" => "image/jpeg",
        "html" => "text/html",
        "csv" => "text/csv",
        "json" => "application/json",
        "md" => "text/markdown",
        _ => "application/octet-stream",
    }
}

fn encode_base64(data: &[u8]) -> String {
    const TABLE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = chunk.get(1).copied().unwrap_or(0) as u32;
        let b2 = chunk.get(2).copied().unwrap_or(0) as u32;
        let triple = (b0 << 16) | (b1 << 8) | b2;
        out.push(TABLE[((triple >> 18) & 0x3f) as usize] as char);
        out.push(TABLE[((triple >> 12) & 0x3f) as usize] as char);
        if chunk.len() > 1 {
            out.push(TABLE[((triple >> 6) & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(TABLE[(triple & 0x3f) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}

#[tauri::command]
fn read_artifact(state: State<AppState>, relative: String) -> Result<ArtifactBody, String> {
    let root = state
        .root
        .lock()
        .map_err(|_| "harness state lock poisoned")?
        .clone()?;
    let path = artifact_path(&root, &relative)?;
    let kind = kind_for(&path)
        .ok_or("this file is not previewed")?
        .to_string();
    let meta = fs::metadata(&path).map_err(|err| err.to_string())?;
    if meta.len() > MAX_PREVIEW_BYTES {
        return Err(format!(
            "{} is {} bytes, over the {} byte preview limit",
            relative,
            meta.len(),
            MAX_PREVIEW_BYTES
        ));
    }
    let bytes = fs::read(&path).map_err(|err| err.to_string())?;
    let mime = mime_for(&kind).to_string();
    if kind == "png" || kind == "jpeg" {
        return Ok(ArtifactBody {
            name: relative,
            kind,
            mime,
            truncated: false,
            text: None,
            base64: Some(encode_base64(&bytes)),
        });
    }
    let text = String::from_utf8_lossy(&bytes).into_owned();
    let truncated = text.chars().count() > MAX_TEXT_CHARS;
    let text = if truncated {
        text.chars().take(MAX_TEXT_CHARS).collect()
    } else {
        text
    };
    Ok(ArtifactBody {
        name: relative,
        kind,
        mime,
        truncated,
        text: Some(text),
        base64: None,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            root: Mutex::new(find_repo_root()),
            starting: Mutex::new(false),
            stdin: Mutex::new(None),
            child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_harness,
            pi_send,
            list_artifacts,
            read_artifact
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                shutdown(app.state::<AppState>().inner());
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jsonl_split_keeps_unicode_line_separators_inside_a_record() {
        let mut buf = "{\"text\":\"line\u{2028}sep\"}\n{\"ok\":true}\n"
            .as_bytes()
            .to_vec();
        let lines = drain_lines(&mut buf);
        assert!(buf.is_empty());
        assert_eq!(lines.len(), 2);
        let first: Value = serde_json::from_slice(&lines[0]).unwrap();
        assert_eq!(first["text"], "line\u{2028}sep");
        let second: Value = serde_json::from_slice(&lines[1]).unwrap();
        assert_eq!(second["ok"], true);
    }

    #[test]
    fn jsonl_split_holds_a_partial_record() {
        let mut buf = b"{\"type\":\"pro".to_vec();
        assert!(drain_lines(&mut buf).is_empty());
        buf.extend_from_slice(b"mpt\"}\r\n");
        let lines = drain_lines(&mut buf);
        assert_eq!(lines.len(), 1);
        assert!(buf.is_empty());
    }

    #[test]
    fn artifact_paths_stay_inside_runs() {
        let root = std::env::temp_dir().join(format!("decoder-desktop-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("runs/nested")).unwrap();
        fs::write(root.join("runs/nested/plot.png"), b"png").unwrap();
        fs::write(root.join("secret.txt"), b"no").unwrap();

        let allowed = artifact_path(&root, "nested/plot.png").unwrap();
        assert!(allowed.ends_with("nested/plot.png"));
        assert!(artifact_path(&root, "../secret.txt").is_err());
        assert!(artifact_path(&root, "/etc/passwd").is_err());
        assert!(artifact_path(&root, "nested/../../secret.txt").is_err());
        assert!(artifact_path(&root, "missing.png").is_err());

        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn base64_matches_known_vectors() {
        assert_eq!(encode_base64(b""), "");
        assert_eq!(encode_base64(b"x"), "eA==");
        assert_eq!(encode_base64(b"hi"), "aGk=");
        assert_eq!(encode_base64(b"hello"), "aGVsbG8=");
    }
}
