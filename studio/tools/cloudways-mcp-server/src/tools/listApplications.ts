import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { jsonContent, toolError } from "../api/utils.js";
import { ServerIdSchema } from "../schemas/server.schema.js";
import { ToolContext } from "./context.js";

export function registerListApplicationsTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "list-cloudways-apps",
    {
      title: "List Cloudways Applications",
      description: "List applications for a Cloudways server.",
      inputSchema: ServerIdSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.applications.listApplications(input.server_id));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

