/**
 * Navigation model + monochrome line icons for the command center.
 *
 * Mirrors archon/ui/gui/sidebar.py `_NAV_GROUPS` and topbar.py `_PAGE_META`
 * so the Tauri surface presents the same architecture: Core → Operate /
 * Intelligence / Automate / Build / Data → System.
 */

export type PageId =
  | "command" | "overview" | "chat"
  | "systems" | "processes" | "files" | "network"
  | "models" | "agents" | "memory"
  | "workflows" | "mcp"
  | "osbuilder" | "projects"
  | "datasets" | "analytics"
  | "logs" | "settings";

export interface NavItem {
  page: PageId;
  label: string;
  icon: string;
}

export const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "COMMAND",
    items: [
      { page: "command", label: "Command", icon: "command" },
      { page: "overview", label: "Overview", icon: "overview" },
      { page: "chat", label: "Chat", icon: "chat" },
    ],
  },
  {
    title: "OPERATE",
    items: [
      { page: "systems", label: "Systems", icon: "systems" },
      { page: "processes", label: "Processes", icon: "processes" },
      { page: "files", label: "Files", icon: "files" },
      { page: "network", label: "Network", icon: "network" },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { page: "models", label: "Models", icon: "models" },
      { page: "agents", label: "Agents", icon: "agents" },
      { page: "memory", label: "Memory", icon: "memory" },
    ],
  },
  {
    title: "AUTOMATE",
    items: [
      { page: "workflows", label: "Workflows", icon: "workflows" },
      { page: "mcp", label: "MCP", icon: "mcp" },
    ],
  },
  {
    title: "BUILD",
    items: [
      { page: "osbuilder", label: "OS Builder", icon: "osbuilder" },
      { page: "projects", label: "Projects", icon: "projects" },
    ],
  },
  {
    title: "DATA",
    items: [
      { page: "datasets", label: "Datasets", icon: "datasets" },
      { page: "analytics", label: "Analytics", icon: "analytics" },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { page: "logs", label: "Logs", icon: "logs" },
      { page: "settings", label: "Settings", icon: "settings" },
    ],
  },
];

/** Human-facing (title, one-line context) per page. */
export const PAGE_META: Record<PageId, [string, string]> = {
  command: ["Command", "Describe an operation — Archon executes it"],
  overview: ["Overview", "System status and recent activity"],
  chat: ["Chat", "Converse with the Archon intelligence layer"],
  systems: ["Systems", "This machine's live hardware and health"],
  processes: ["Processes", "Live process table for this machine"],
  files: ["Files", "Browse the local filesystem (read-only)"],
  network: ["Network", "Interfaces, addresses, and throughput"],
  models: ["Models", "The intelligence Archon routes tasks to"],
  agents: ["Agents", "Autonomous operations on Archon's behalf"],
  memory: ["Memory", "What Archon knows about your environment"],
  workflows: ["Workflows", "Browse, trigger, and monitor n8n workflows"],
  mcp: ["MCP", "Capabilities that extend Archon's reach"],
  osbuilder: ["OS Builder", "Compose and build a custom Linux image"],
  projects: ["Projects", "Architecture, decisions, tasks, artifacts"],
  datasets: ["Datasets", "Query and summarize data as an instrument"],
  analytics: ["Analytics", "Aggregations and insights"],
  logs: ["Logs", "Past operations and their results"],
  settings: ["Settings", "Configuration and preferences"],
};

/** 24×24 stroke icon path data, keyed by icon name. */
export const ICON_PATHS: Record<string, string> = {
  command: "M4 6h16M4 12h10M4 18h7",
  overview: "M4 4h7v7H4zM13 4h7v4h-7zM13 11h7v9h-7zM4 14h7v6H4z",
  chat: "M4 5h16v10H8l-4 4z",
  systems: "M4 5h16v10H4zM9 19h6M12 15v4",
  processes: "M4 5h16v14H4zM4 9h16M8 5v14",
  files: "M4 5h6l2 3h8v11H4z",
  network: "M12 3v4M12 17v4M3 12h4M17 12h4M12 8a4 4 0 100 8 4 4 0 000-8z",
  models: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 3v18M4 7.5l8 4.5 8-4.5",
  agents: "M12 3a4 4 0 014 4v2a4 4 0 01-8 0V7a4 4 0 014-4zM5 21v-2a5 5 0 015-5h4a5 5 0 015 5v2",
  memory: "M6 4h12v16H6zM9 8h6M9 12h6M9 16h4",
  workflows: "M5 6a2 2 0 104 0 2 2 0 00-4 0zM15 18a2 2 0 104 0 2 2 0 00-4 0zM7 8v4a4 4 0 004 4h4",
  mcp: "M12 3l7 4v10l-7 4-7-4V7zM12 12l7-4M12 12v9M12 12L5 8",
  osbuilder: "M4 7l8-4 8 4v10l-8 4-8-4zM4 7l8 4 8-4M12 11v10",
  projects: "M4 6h16v14H4zM4 6l3-3h5l2 3M4 11h16",
  datasets: "M4 6c0-1.5 3.6-2.5 8-2.5s8 1 8 2.5-3.6 2.5-8 2.5-8-1-8-2.5zM4 6v12c0 1.5 3.6 2.5 8 2.5s8-1 8-2.5V6",
  analytics: "M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-7",
  logs: "M6 3h9l3 3v15H6zM9 8h6M9 12h6M9 16h4",
  settings: "M12 9a3 3 0 100 6 3 3 0 000-6zM19 12l2-1-1-3-2 .5a7 7 0 00-1.5-1.5L16 4h-3l-.5 2a7 7 0 00-2 .8L8 5.5 5.5 8 7 9.5A7 7 0 006 12l-2 .5 1 3 2-.5a7 7 0 001.5 1.5L8 19h3l.5-2a7 7 0 002-.8l1.5 1.3 2.5-2.5-1.3-1.5z",
};

/** Build an inline SVG icon element. */
export function icon(name: string, size = 18): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.6");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", ICON_PATHS[name] ?? ICON_PATHS.command);
  svg.appendChild(path);
  return svg;
}
