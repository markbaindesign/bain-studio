import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { jsonContent, toolError } from "../api/utils.js";
import { ServerIdSchema } from "../schemas/server.schema.js";
import { ToolContext } from "./context.js";

export function registerGetServerStatsTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "get-server-stats",
    {
      title: "Get Server Stats",
      description: "Fetch CPU, RAM, disk, uptime, and load information for a Cloudways server.",
      inputSchema: ServerIdSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.monitoring.getServerStats(input.server_id));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

