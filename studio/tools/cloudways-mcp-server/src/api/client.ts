import axios, { AxiosInstance, AxiosRequestConfig, Method } from "axios";
import { CloudwaysAuth } from "./auth.js";
import { normalizeBaseUrl, optionalEnv, unwrapData } from "./utils.js";

export class CloudwaysClient {
  private readonly http: AxiosInstance;
  private readonly baseUrl: string;
  private readonly auth: CloudwaysAuth;

  constructor() {
    this.baseUrl = normalizeBaseUrl(optionalEnv("CLOUDWAYS_API_BASE_URL", "https://api.cloudways.com/api/v1")!);
    this.http = axios.create({
      timeout: Number(process.env.CLOUDWAYS_TIMEOUT_MS ?? 30_000),
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });
    this.auth = new CloudwaysAuth(this.http, this.baseUrl);
  }

  async request<T = unknown>(method: Method, path: string, data?: unknown, config: AxiosRequestConfig = {}): Promise<T> {
    const token = await this.auth.getAccessToken();
    const response = await this.http.request<T>({
      ...config,
      method,
      url: `${this.baseUrl}${path}`,
      data,
      headers: {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      },
    });
    return unwrapData<T>(response.data);
  }
}

