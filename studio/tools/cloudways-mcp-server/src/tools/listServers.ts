import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { ServerFilterSchema } from "../schemas/server.schema.js";
import { ToolContext } from "./context.js";

const InputSchema = z.object({
  filter: ServerFilterSchema.optional(),
});

export function registerListServersTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "list-cloudways-servers",
    {
      title: "List Cloudways Servers",
      description: "List Cloudways servers with optional status filtering.",
      inputSchema: InputSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.servers.listServers(input.filter ?? "all"));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

