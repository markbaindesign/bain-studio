import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { jsonContent, toolError } from "../api/utils.js";
import { AppTargetSchema } from "../schemas/app.schema.js";
import { ToolContext } from "./context.js";

const InputSchema = AppTargetSchema.extend({
  action: z.enum(["list", "enable_auto", "install_custom"]),
  certificate_content: z.string().optional(),
  key_content: z.string().optional(),
});

export function registerManageSslTool(server: McpServer, context: ToolContext) {
  server.registerTool(
    "manage-ssl-certificate",
    {
      title: "Manage SSL Certificate",
      description: "List, enable automatic SSL, or install a custom SSL certificate for an app.",
      inputSchema: InputSchema,
    },
    async (input) => {
      try {
        if (input.action === "install_custom" && (!input.certificate_content || !input.key_content)) {
          return toolError("certificate_content and key_content are required for install_custom");
        }

        return jsonContent(
          await context.ssl.manageCertificate(
            input.server_id,
            input.app_id,
            input.action,
            input.certificate_content,
            input.key_content,
          ),
        );
      } catch (error) {
        return toolError(error);
      }
    },
  );
}

