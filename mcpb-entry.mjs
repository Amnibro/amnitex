import { spawn, execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { homedir, platform, arch } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const root = dirname(fileURLToPath(import.meta.url));
const cacheDir = join(homedir(), ".cache", "amnitex");
const cachedBin = join(cacheDir, "atex");
const linuxBin = join(root, "bin", "atex-linux-x64");
let bin = cachedBin;
if (platform() === "linux" && arch() === "x64" && existsSync(linuxBin)) {
  bin = linuxBin;
} else if (!existsSync(cachedBin)) {
  mkdirSync(cacheDir, { recursive: true });
  const srcC = join(root, "src", "atex.c");
  const incDir = join(root, "src");
  execFileSync("cc", ["-O3", `-I${incDir}`, srcC, "-lm", "-lpthread", "-o", cachedBin], { stdio: "ignore" });
}
const kbDir = process.env.ATEX_DIR && process.env.ATEX_DIR.trim() ? process.env.ATEX_DIR.trim() : join(homedir(), ".atex");
const child = spawn(bin, ["serve", "--atex-dir", kbDir], { stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
