import { spawn, execFileSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync } from "node:fs";
import { homedir, platform, arch } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const root = dirname(fileURLToPath(import.meta.url));
const prebuilt = {
  "linux-x64": "atex-linux-x64",
  "darwin-arm64": "atex-macos-arm64",
  "darwin-x64": "atex-macos-x64",
  "win32-x64": "atex-windows-x64.exe",
  "win32-arm64": "atex-windows-x64.exe",
}[`${platform()}-${arch()}`];
let bin = prebuilt ? join(root, "bin", prebuilt) : "";
if (bin && existsSync(bin)) {
  if (platform() !== "win32") { try { chmodSync(bin, 0o755); } catch {} }
} else {
  const cacheDir = join(homedir(), ".cache", "amnitex");
  bin = join(cacheDir, "atex");
  if (!existsSync(bin)) {
    mkdirSync(cacheDir, { recursive: true });
    const src = join(root, "src");
    execFileSync("cc", ["-O3", "-fwrapv", "-w", `-I${src}`, join(src, "atex.c"), "-lm", "-lpthread", "-o", bin], { stdio: "ignore" });
  }
}
let kbDir = process.env.ATEX_DIR && process.env.ATEX_DIR.trim() ? process.env.ATEX_DIR.trim() : join(homedir(), ".atex");
if (platform() === "win32") kbDir = kbDir.replace(/\\/g, "/");
const child = spawn(bin, ["serve", "--atex-dir", kbDir], { stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
