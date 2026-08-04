import { z } from "zod";

export const AppTargetSchema = z.object({
  server_id: z.string().min(1),
  app_id: z.string().min(1),
});

