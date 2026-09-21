import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const skillsDir = join(repoRoot, "skills");

const QLEVER_MCP_NAME = "decoder";
const QLEVER_MCP_URL = "https://qlever-test.geocodes-aws-dev.earthcube.org/ec/api/mcp";
const MCP_RUNTIME_REGISTER_EVENT = "pi-mcp-adapter:runtime-register:v1";

type McpRuntimeRegistration = { dispose(): Promise<void> };
type McpRuntimeRegistrationRequest = {
	version: 1;
	name: string;
	definition: { url: string; lifecycle: "keep-alive" };
	result?:
		| { ok: true; registration: McpRuntimeRegistration }
		| { ok: false; error: Error };
};

function localSkillNames(): string[] {
	if (!existsSync(skillsDir)) {
		return [];
	}
	return readdirSync(skillsDir, { withFileTypes: true })
		.filter((entry) => entry.isDirectory() && existsSync(join(skillsDir, entry.name, "SKILL.md")))
		.map((entry) => entry.name)
		.sort();
}

export default function (pi: ExtensionAPI) {
	let qleverRegistration: McpRuntimeRegistration | undefined;

	pi.on("resources_discover", () => {
		return { skillPaths: [skillsDir] };
	});

	pi.on("session_start", async (_event, ctx) => {
		// Emit here, not at load, so pi-mcp-adapter has installed its listener.
		if (!qleverRegistration) {
			const request: McpRuntimeRegistrationRequest = {
				version: 1,
				name: QLEVER_MCP_NAME,
				definition: { url: QLEVER_MCP_URL, lifecycle: "keep-alive" },
			};
			pi.events.emit(MCP_RUNTIME_REGISTER_EVENT, request);
			if (request.result?.ok) {
				qleverRegistration = request.result.registration;
			} else {
				const detail = request.result?.ok === false ? request.result.error.message : "pi-mcp-adapter is not installed";
				const message = `${QLEVER_MCP_NAME} MCP: ${detail}`;
				if (ctx.hasUI) {
					ctx.ui.notify(message, "warning");
				} else {
					console.error(message);
				}
			}
		}

		if (!ctx.hasUI) {
			return;
		}
		const names = localSkillNames();
		const label = names.length > 0 ? names.join(", ") : "(none)";
		ctx.ui.notify(`decoder-pi skills: ${label}`, "info");
	});

	pi.on("session_shutdown", async () => {
		const current = qleverRegistration;
		qleverRegistration = undefined;
		await current?.dispose();
	});
}
