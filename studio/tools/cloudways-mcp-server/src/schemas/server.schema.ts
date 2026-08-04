import { z } from "zod";

export const ServerFilterSchema = z.enum(["running", "stopped", "all"]).default("all");

export const ServerIdSchema = z.object({
  server_id: z.string().min(1),
});

