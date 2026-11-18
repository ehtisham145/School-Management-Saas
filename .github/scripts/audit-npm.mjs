// Fails on any high or critical advisory in the production npm packages, except the
// ones listed here. Each exception ends on its own date, so it has to be looked at again.
// Run from the frontend folder: node ../.github/scripts/audit-npm.mjs
import { spawnSync } from "node:child_process";

const EXCEPTIONS = {
  // picomatch ReDoS. No fixed version exists yet (latest is 4.0.7). It needs an attacker to
  // supply the glob pattern, and our patterns are fixed. It comes in through next-intl's
  // message extractor, a build tool that the running site doesn't use.
  "GHSA-fc5q-39xc-vjpf": "2026-12-18",
};

const audit = spawnSync("npm audit --omit=dev --json", {
  encoding: "utf8",
  shell: true,
  maxBuffer: 50 * 1024 * 1024,
});
const report = JSON.parse(audit.stdout);
if (!report.vulnerabilities) {
  console.error(
    "npm audit did not return a report:",
    audit.stdout.slice(0, 500),
  );
  process.exit(1);
}

const today = new Date().toISOString().slice(0, 10);
const advisories = new Map();
for (const { via } of Object.values(report.vulnerabilities)) {
  for (const item of via) {
    if (
      typeof item === "object" &&
      ["high", "critical"].includes(item.severity)
    ) {
      advisories.set(item.url.split("/").pop(), item);
    }
  }
}

let failed = false;
for (const [id, advisory] of advisories) {
  const until = EXCEPTIONS[id];
  if (until && today <= until) {
    console.log(
      `Allowed until ${until}: ${id} (${advisory.name}) ${advisory.title}`,
    );
  } else {
    failed = true;
    console.error(
      `${advisory.severity}: ${id} (${advisory.name}) ${advisory.title}`,
    );
  }
}

if (failed) process.exit(1);
console.log("No high or critical advisories need action.");
