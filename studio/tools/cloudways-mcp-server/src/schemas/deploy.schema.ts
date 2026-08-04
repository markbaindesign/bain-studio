import { z } from "zod";

export const DeploySchema = z.object({
  server_id: z.string().min(1),
  app_id: z.string().min(1),
  git_branch: z.string().min(1).default("main"),
  commit_message: z.string().optional(),
});

export const DeploymentStatusSchema = z.object({
  server_id: z.string().min(1),
  app_id: z.string().min(1),
  deployment_id: z.string().min(1),
});

