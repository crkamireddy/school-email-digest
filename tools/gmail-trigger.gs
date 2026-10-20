/**
 * Gmail → GitHub trigger for School Email Digest.
 *
 * Runs inside your own Google account (Google Apps Script), every few
 * minutes. When a new email with your digest label shows up, it asks
 * GitHub to start the digest workflow right away, instead of waiting
 * for the next scheduled run. Setup steps are in the README, Part 3.
 *
 * It only reads the received time of labeled emails — never subjects,
 * senders or content — and its Gmail permission is read-only (set in
 * gmail-trigger.appsscript.json, which you paste in as appsscript.json). All the real work (reading, summarizing, posting) still
 * happens in the GitHub workflow, which catches up on everything since
 * its last run. So a missed or extra trigger is harmless: a missed one
 * is picked up by the next trigger or the backstop schedule, and an
 * extra one makes a run that finds nothing new.
 */

// ---- Edit these three to match your setup ---------------------------

// Your GitHub repository, as "owner/name".
const GITHUB_REPO = 'your-github-name/your-repo-name';

// The same Gmail label as `gmail: label:` in your config.yaml.
const GMAIL_LABEL = 'School';

// How often to check Gmail. Apps Script allows 1, 5, 10, 15 or 30.
const CHECK_EVERY_MINUTES = 5;

// ---------------------------------------------------------------------
// The GitHub token is NOT stored here, so it can't leak if you share
// or copy this code. Put it in Project Settings → Script Properties,
// under the name GITHUB_TOKEN.

const WORKFLOW_FILE = 'run-digest.yml';
const BRANCH = 'main';
const LAST_SEEN_KEY = 'lastSeenEmailMillis';

/**
 * Run this once by hand (select it in the toolbar, click Run). It
 * removes any old copies of the timer and starts a fresh one, so it's
 * safe to run again after changing CHECK_EVERY_MINUTES.
 */
function installTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'checkForNewEmail')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('checkForNewEmail')
    .timeBased()
    .everyMinutes(CHECK_EVERY_MINUTES)
    .create();
  // Run one check now, so the authorization prompt and any setup
  // mistakes show up immediately rather than in 5 minutes.
  checkForNewEmail();
}

/** Run this by hand to stop the trigger. */
function removeTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'checkForNewEmail')
    .forEach(t => ScriptApp.deleteTrigger(t));
}

/**
 * The timer calls this. It remembers the time of the newest labeled
 * email it has already reported, and starts the workflow only when a
 * newer one appears. Comparing email times (rather than "when did I
 * last check") means an email that takes a minute to show up in
 * Gmail's search still gets noticed on a later check, without the same
 * email triggering twice.
 */
function checkForNewEmail() {
  const props = PropertiesService.getScriptProperties();

  // Only the last two days, to keep the search small. Anything older
  // than that is covered by the backstop schedule. Gmail lists newest
  // first; the few most recent are plenty to find the newest one.
  const list = Gmail.Users.Messages.list('me', {
    q: `label:${GMAIL_LABEL} newer_than:2d`,
    maxResults: 5,
  });
  const messages = list.messages || [];
  if (messages.length === 0) return;

  // 'minimal' fetches only IDs, labels and the received time — no
  // subject, sender or body.
  const newest = Math.max(...messages.map(m =>
    Number(Gmail.Users.Messages.get('me', m.id, { format: 'minimal' }).internalDate)
  ));

  const lastSeen = Number(props.getProperty(LAST_SEEN_KEY) || 0);
  if (newest <= lastSeen) return;

  startWorkflow(props.getProperty('GITHUB_TOKEN'));

  // Saved only after GitHub accepted the request. If the call failed
  // (startWorkflow throws), the next check tries again.
  props.setProperty(LAST_SEEN_KEY, String(newest));
}

function startWorkflow(token) {
  if (!token) {
    throw new Error('No GITHUB_TOKEN in Script Properties — see README Part 3.');
  }
  const url = `https://api.github.com/repos/${GITHUB_REPO}` +
              `/actions/workflows/${WORKFLOW_FILE}/dispatches`;
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
    },
    // `trigger: gmail` tells the workflow this isn't a person clicking
    // "Run workflow", so it respects the DIGEST_ENABLED off switch.
    payload: JSON.stringify({ ref: BRANCH, inputs: { trigger: 'gmail' } }),
    muteHttpExceptions: true,
  });
  // GitHub answers 204 (No Content) when the run was queued.
  if (response.getResponseCode() !== 204) {
    throw new Error(
      `GitHub refused to start the workflow (HTTP ${response.getResponseCode()}): ` +
      response.getContentText()
    );
  }
}
