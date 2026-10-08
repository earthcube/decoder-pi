import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const repoRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const skillsDir = join(repoRoot, "skills");

const QLEVER_MCP_NAME = "decoder";
const QLEVER_MCP_URL = "https://qlever-test.geocodes-aws-dev.earthcube.org/ec/api/mcp";

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
	// Register at load so builtin:mcp connects this with .pi/mcp.json servers.
	pi.registerMcpServer(QLEVER_MCP_NAME, { url: QLEVER_MCP_URL });

	pi.on("resources_discover", () => {
		return { skillPaths: [skillsDir] };
	});

	pi.on("session_start", (_event, ctx) => {
		if (!ctx.hasUI) {
			return;
		}
		const names = localSkillNames();
		const label = names.length > 0 ? names.join(", ") : "(none)";
		ctx.ui.notify(`decoder-pi skills: ${label}`, "info");
	});
}
