# Decoder desktop

A Tauri window for this harness. The window supervises `./bin/pi --mode rpc` and renders the transcript, tool calls, and previewable files under `runs/`. It does not reimplement skills, SPARQL, plotting, or MCP.

Requirements are the same as the CLI: `pi` and `uv` on `PATH`, plus a Rust toolchain and WebKitGTK for the window.

The app looks for this repo by walking up from the working directory. If that fails, set `DECODER_PI_ROOT` to the checkout that contains `bin/pi`.

## Development server

```bash
cd desktop
npm install
npm run tauri dev
```

## Release build

From `desktop/`, after `npm install`:

```bash
npm run tauri build
```

That typechecks and bundles the page, then compiles the Rust window in release mode. The binary is `desktop/src-tauri/target/release/desktop`. Installable packages, when the bundler finishes, land under `desktop/src-tauri/target/release/bundle/`. On Linux the config asks for every package type, so that step also wants the usual `.deb`, `.rpm`, and AppImage tools. The binary itself is already built before that packaging step.

The release binary is only the window. Skills, `extensions/load-skills.ts`, `.mcp.json`, and the Python tools stay in this checkout. Run the binary from the checkout, or set `DECODER_PI_ROOT` to it. It still launches `bin/pi` and expects `pi` and `uv` on `PATH`.

Sessions are the normal Pi session files for this repo, so a later `./bin/pi --continue` can pick up a desktop conversation. Closing the window closes Pi's stdin and waits for that process to exit.
