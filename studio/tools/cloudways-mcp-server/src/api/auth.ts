import { AxiosInstance } from "axios";
import { getEnv } from "./utils.js";

/**
 * Cloudways now issues CLOUDWAYS_API_TOKEN as a ready-to-use bearer access
 * token (no email+api_key OAuth exchange step exists for it) — confirmed by
 * calling GET /server directly with it as `Authorization: Bearer`.
 */
export class CloudwaysAuth {
  constructor(
    private readonly http: AxiosInstance,
    private readonly baseUrl: string,
  ) {}

  async getAccessToken(): Promise<string> {
    return getEnv("CLOUDWAYS_API_TOKEN");
  }
}

