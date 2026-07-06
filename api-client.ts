/**
 * API 客户端
 *
 * 使用 @tego/shared 的 createHttpClient 保持一致性
 *
 * URL 优先级：
 * 1. localStorage 中用户设置的 API Base URL（支持运行时修改）
 * 2. VITE_API_URL 环境变量（编译时配置）
 * 3. Tauri 环境下默认 http://localhost:3000（SSE/WebSocket 需要绝对地址）
 * 4. 空字符串（浏览器开发环境使用相对路径，通过 Vite proxy 代理）
 *
 * 在 Tauri 生产模式中，Rust 协议代理（proxy.rs）处理 tauri://localhost
 * 下的相对路径请求作为兜底层。此处返回绝对 URL 主要保证 EventSource、
 * WebSocket 等不经过协议处理器的场景也能正常工作。
 */

import { createHttpClient, type HttpClient } from '@tego/shared';

import { IS_TAURI } from './platform';
import { getApiBaseUrl as getStoredApiBaseUrl } from './storage';

export type { HttpClient };

const DEFAULT_API_URL = 'http://localhost:3000';
const BUILD_DEPLOYMENT_MODE = import.meta.env.VITE_DEPLOYMENT_MODE?.trim();

function shouldUseStoredApiBaseUrl(): boolean {
    // Public SaaS desktop builds carry a brand-baked API URL and do not expose
    // server settings on the login page. Ignore stale overrides left by older
    // private/local builds so users are not stranded with an empty login panel.
    return !(IS_TAURI && BUILD_DEPLOYMENT_MODE === 'saas');
}

/**
 * 获取 API 基础 URL
 * 优先使用用户在设置中配置的 URL，其次使用环境变量。
 * 公共 SaaS 桌面包例外：始终使用构建/品牌内置 URL，避免旧配置覆盖。
 */
export function getApiBaseUrl(): string {
    if (shouldUseStoredApiBaseUrl()) {
        const storedUrl = getStoredApiBaseUrl();
        if (storedUrl) return storedUrl;
    }

    if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;

    // Tauri 环境下必须返回绝对 URL：EventSource / WebSocket 等持久连接
    // 无法走 tauri:// 协议代理（不支持流式响应）
    if (IS_TAURI) return DEFAULT_API_URL;

    return '';
}

function getHttpApiBaseUrl(): string {
    return '';
}

// Strip trailing slashes from base so that `${base}${path}` never produces
// double slashes (which Hono's router treats as a different — and missing — route).
function normalizeBase(baseUrl: string): string {
    return baseUrl.replace(/\/+$/, '');
}

/**
 * 构建完整的 API URL
 * @param path API 路径（如 /api/v1/tego-os/auth）
 */
export function buildApiUrl(path: string): string {
    const baseUrl = normalizeBase(getHttpApiBaseUrl());
    return baseUrl ? `${baseUrl}${path}` : path;
}

/**
 * 创建 API 客户端
 * 注意：这个函数在调用时会读取当前的 baseUrl，
 * 如果 baseUrl 变化，需要重新创建客户端
 */
export function createApiClient(basePath: string): HttpClient {
    const baseUrl = normalizeBase(getHttpApiBaseUrl());
    const baseURL = baseUrl ? `${baseUrl}${basePath}` : basePath;
    return createHttpClient({ baseURL });
}

// 默认 API 客户端（注意：baseUrl 变化后需要刷新页面）
export const apiClient = createApiClient('/api/v1/tego-os');
