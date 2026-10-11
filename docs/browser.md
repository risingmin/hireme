# Codex browser adapter

The application workflow uses connected **real Chrome**, with its existing sign-ins.
The Claude CLI `--chrome` switch is not a Codex switch. Configure the browser MCP/plugin
for the Codex runtime you actually use. Tools in a desktop chat are not proof that a
scheduled `codex exec` session has them. Keep the desktop app and Chrome awake and connected.

## Preflight and ownership

Before sourcing or entering any personal data, discover tools and read their current
documentation. Verify Chrome is connected and supports clicks, typing, file upload, and
saved screenshots. No connection or required capability: log NEEDS HUMAN and exit.
Never use a headless browser, remote debugging, direct submission HTTP calls, or page
JavaScript to mutate forms as a fallback. Never manufacture behavior to evade a detector.
Successful trusted input does not guarantee an ATS will accept an application.

Create a fresh tab and retain its id as the ownership record. An inventory may include
personal tabs: do not read their content, claim, navigate, or close them. Reuse your own
tab across postings. Do not reclaim stale tabs from another session by guessing ownership.
Close your own tabs when done; preserve the one deliberately handed to the user.
After a dropped connection, re-observe state. If submit might have happened, record
SUBMISSION UNCERTAIN and reconcile the confirmation/history before retrying.

## Unified `cua_repl` API

Use the runtime's current documentation; do not import an external Playwright package.
On first use, make exactly one supported discovery/selection call, then read its result.
For discovery: `await cua.listBrowsers()`; choose the actual extension-backed Chrome id.
Select with `await cua.getBrowser({id: observedId})`, read the returned browser docs,
name the session, then create a tab using `cua.createBrowserTab("chrome", url,
{sessionName: "Job applications"})` with the session naming format required by the runtime.

Use fresh `tab.getAXState()` indices with `tab.click(index)` and
`tab.typeText(index, confirmedValue)`. After actions, get fresh state before deciding
the next action. Use documented semantic locators when the accessibility API lacks a
capability. Evaluation is read-only: inspect values, validity, and visible structure only.
Never call DOM setters, dispatch events, fetch a submission endpoint, or click via eval.
Do not use keyboard Return where it could accidentally submit a form.

Read the runtime's `file-uploads` documentation. The current chooser flow is:

```js
const chooserPromise = tab.playwright.waitForEvent("filechooser", {timeoutMs: 10000});
await tab.playwright.locator('input[type="file"]').click();
const chooser = await chooserPromise;
await chooser.setFiles([absoluteResumePath]);
```

Paths come from profile.json and must exist on the browser's machine. Check iframe
support from the actual tool documentation; do not assume all cross-origin uploads fail.
If necessary open a verified canonical company ATS URL instead of its embedded form.
Unsupported upload: NEEDS HUMAN. Do not use the legacy resume server or DataTransfer hack.

Capture screenshot bytes using the documented screenshot method, and save them directly
under `screenshots/`. Read `screenshots` documentation first. The current Chrome runtime
returns JPEG. Standard Node filesystem export was verified in the unified REPL:

```js
const fs = await import('node:fs/promises');
const bytes = await tab.getScreenshot({emit: false});
await fs.writeFile('/absolute/repo/screenshots/company-role.jpg', bytes);
```

Use an observed tab handle, an actual repo path, and the documented screenshot method.
Filesystem export does not operate the browser. If a runtime supplies PNG instead, save
a genuine PNG and record its format rather than renaming the extension. Never export GIFs
or use Downloads.
No screenshot-save capability: stop before submitting. Embed proof in the interactive reply.
Close with `tab.close()`. For intentional handoffs, call `tab.markHandoff()` before ending
the turn; marks may need refreshing after another turn. Do not mark routine research tabs.

## Extension MCP compatibility

If the connected runtime instead provides documented `mcp__claude-in-chrome__*` tools,
use their actual schemas: `tabs_context_mcp`, create a new owned tab, `computer` input,
`file_upload`, read-only `javascript_tool`, and close only the owned tab ids. Tool names
alone do not establish a Claude dependency. Respect site permissions and never assume
every tab returned belongs to you. Follow the runtime's browser skill.

## Portals, codes, and approvals

Preserve `channels.signed_in_portals`. Confirm the signed-in header before using a portal.
Never sign in, create accounts, type passwords, or request login codes. Expired sessions
are NEEDS HUMAN. LinkedIn and curated lists are sources; apply on the company ATS.

The optional macOS Gmail broker remains `scripts/code_broker.py`. For a post-submit
verification only, obtain the submit timestamp, call the broker, and paste the concealed
code with native Cmd+V, then confirm. Never read the clipboard, code field, email body,
or Keychain. Never screenshot between paste and confirmation. If a browser backend cannot
paste without exposing the code through observations, stop for human completion. The
broker uses macOS native clipboard APIs internally; the agent invokes it as an opaque
helper and does not reproduce those APIs in browser code.

An unattended schedule does not override runtime approvals for sensitive transmissions,
legal agreements, or site access. If an action requires a human, log NEEDS HUMAN and stop
that application. Interactive runs show exact data and destination before requesting
any required confirmation. No login or CAPTCHA exceptions are added by the port.
