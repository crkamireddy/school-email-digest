# Privacy Policy

**School Email Digest** is a personal, self-hosted tool. Each person who
uses it runs their own copy, with their own Google, Anthropic, and Slack
accounts. The author of this project never receives, sees, or stores
any of your data.

## What it accesses

- **Gmail (read-only).** The tool asks for `gmail.readonly` permission,
  but only ever searches for emails carrying the single label you set in
  your own `config.yaml`. It cannot send, delete, or modify email.
- **Google Drive (only its own file).** If you turn on Drive sync, the
  tool uses the `drive.file` permission, which only allows access to
  files the tool itself created — in practice, one sent-log file in the
  folder you choose. It cannot see the rest of your Drive.

## Where your data goes

- The text of each labeled email is sent to the **Anthropic API** (using
  your own API key) to pull out the relevant items.
- A short summary of the relevant items is posted to the **Slack channel**
  you configure (using your own Slack bot token).

Nothing is sent anywhere else. There are no analytics, ads, or tracking.

## What it stores

A small database (the "sent log") records what has already been posted,
so it doesn't repeat itself: a short topic label, the school name, a
one-line summary, the Gmail message ID, and the date. It's kept on your
own computer, or in your own Google Drive if you turn on Drive sync. It
does not store full email contents.

## Removing access

You can revoke the tool's Google access at any time at
<https://myaccount.google.com/permissions>, and delete the sent-log file
from your computer or Drive.

## Contact

Questions: open an issue on this repository.
