/**
 * vr-psp-live 24/7 触发器（Cloudflare Worker + Cron Trigger）
 *
 * 作用：每 10 分钟调用一次 GitHub API，触发 refresh-and-deploy 工作流。
 * 为什么需要：GitHub 自己的 `schedule` 是 best-effort，实测会被降频到数小时一次
 *            （最近三天中位间隔约 4.8 小时）；而 `workflow_dispatch` 触发的运行会立刻执行。
 *            抓取仍然由 GitHub 的机器完成，所以不受 B 站对 Cloudflare 出口的风控影响。
 *
 * 需要配置：
 *   Secret  GH_TOKEN  细粒度令牌：仅 kaornao/vr-psp-live、仅 Actions: Read and write
 *   Cron    每 10 分钟触发一次（在 Settings → Triggers → Cron Triggers 添加；表达式见同目录 部署说明.md）
 * 可选：
 *   Secret  RUN_KEY   配置后可用 /run?key=<值> 手动触发一次，便于自检
 *
 * 接口：
 *   GET /              返回运行状态（是否已配令牌、上次触发结果），不产生副作用
 *   GET /run?key=...   手动触发一次（需要 RUN_KEY）
 */

const OWNER = "kaornao";
const REPO = "vr-psp-live";
const WORKFLOW = "refresh-and-deploy.yml";
const REF = "main";
const API = "https://api.github.com/repos/" + OWNER + "/" + REPO + "/actions/workflows/" + WORKFLOW + "/dispatches";

let last = { at: null, status: null, note: null };

function json(body, status) {
  return new Response(JSON.stringify(body, null, 2), {
    status: status || 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

async function dispatch(env) {
  const token = env && env.GH_TOKEN;
  if (!token) return { ok: false, status: 0, note: "GH_TOKEN 未配置" };
  let res;
  try {
    res = await fetch(API, {
      method: "POST",
      headers: {
        Authorization: "Bearer " + token,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vr-psp-live-cron-trigger",
      },
      body: JSON.stringify({ ref: REF }),
    });
  } catch (e) {
    last = { at: new Date().toISOString(), status: 0, note: String(e) };
    return { ok: false, status: 0, note: String(e) };
  }
  const text = await res.text();
  const out = { ok: res.status === 204, status: res.status, note: text.slice(0, 200) || "ok" };
  last = { at: new Date().toISOString(), status: out.status, note: out.note };
  return out;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (path === "/run") {
      if (!env.RUN_KEY || url.searchParams.get("key") !== env.RUN_KEY) {
        return json({ ok: false, error: "需要配置 RUN_KEY 且 key 正确" }, 403);
      }
      const r = await dispatch(env);
      return json(r, r.ok ? 200 : 502);
    }

    if (path === "/") {
      return json(
        {
          ok: true,
          service: "vr-psp-live-cron-trigger",
          target: OWNER + "/" + REPO + " " + WORKFLOW + " ref=" + REF,
          hasToken: Boolean(env && env.GH_TOKEN),
          hasRunKey: Boolean(env && env.RUN_KEY),
          lastDispatchAt: last.at,
          lastStatus: last.status,
          lastNote: last.note,
          now: new Date().toISOString(),
        },
        200
      );
    }

    return json({ ok: false, error: "未知路径：" + path }, 404);
  },
};