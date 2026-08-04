import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { ToolContext } from "./context.js";

const InputSchema = z.object({
  server_id: z.string().min(1),
  service: z.enum(["php", "nginx", "mysql", "redis", "all"]),
});

export function registerRestartServiceTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "restart-cloudways-service",
    {
      title: "Restart Cloudways Service",
      description: "Restart a Cloudways server service. Endpoint may need adjustment for Cloudways API V2.",
      inputSchema: InputSchema,
    },
    async (input) => {
      try {
        return jsonContent(await context.servers.restartService(input.server_id, input.service));
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

