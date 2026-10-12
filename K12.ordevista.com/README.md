# Ordevista K-12 Resources — landing page on AWS

A permanent, privacy-respecting home for every session resource (current and future),
at one short URL you can print on sticky notes: **https://k12.ordevista.com**

## How it fits together (analogy)

Think of it as a **library**:

| Library | AWS piece | What it does |
|---|---|---|
| Stockroom (locked, no public entry) | **S3 bucket** (private, encrypted, versioned) | Holds the page, logos, and PDFs |
| Front desk that fetches books for visitors | **CloudFront** + Origin Access Control | The *only* way in; caches copies at the edge |
| Building ID badge | **ACM certificate** | HTTPS for k12.ordevista.com |
| Street address sign | **Bluehost DNS** CNAME record | Points k12.ordevista.com at CloudFront |
| House rules posted at the door | **Response headers policy** | HSTS, CSP, no framing, no camera/mic/location |
| Card catalog | `content/resources.json` | The single list you edit to add resources |

The URL on the sticky note never changes; only the catalog behind it does.

## Folder layout

```
content/resources.json   ← edit this to add/retire resources
content/files/           ← drop PDFs here (served at /files/<name>)
content/assets/           ← site icons (Ordevista logo) and partner logos/
src/                     ← page template, styles, builder (no dependencies)
infra/site.yaml          ← CloudFormation template (all AWS resources)
deploy-infra.sh          ← create/update the AWS stack (run once)
publish.sh               ← build + upload + refresh CDN (run every update)
```

## One-time setup

Prerequisites: AWS CLI v2 signed in to the Ordevista account (`aws sts get-caller-identity`),
Python 3, and your Bluehost login. DNS for ordevista.com is managed at Bluehost
(nameservers ns1/ns2.bluehost.com), so you add two records there by hand.

### 1. Start the AWS deployment

```
./deploy-infra.sh
```

After a minute the script prints **Bluehost step 1**: a certificate validation record.
Keep the terminal open; the script waits while you add it.

### 2. Add the records in Bluehost

Open the DNS editor:

1. Log in to Bluehost. Go to **Domains**, find **ordevista.com**, click **Manage**, then **DNS**.
   (Alternative route: **Advanced → cPanel → Zone Editor → Manage** next to ordevista.com.)
2. Scroll to **CNAME (Alias)** records and click **Add Record**.

**Record 1: certificate validation** (from the script's step 1 output)

| Field | Enter | Example |
|---|---|---|
| Host Record | the `Host` value the script printed | `_3f9a1c...k12` |
| Points To | the `Points To` value the script printed | `_7b2e...acm-validations.aws` |
| TTL | leave the default | |

Save it. Within roughly 5–30 minutes, AWS sees the record, issues the certificate, and the
script moves on to creating CloudFront (another 5–10 minutes). It then prints **Bluehost step 2**.

**Record 2: the site address** (from the script's step 2 output)

| Field | Enter | Example |
|---|---|---|
| Host Record | `k12` | `k12` |
| Points To | the CloudFront domain the script printed | `d1a2b3c4d5e6f7.cloudfront.net` |
| TTL | leave the default | |

### 3. Publish the page

```
./publish.sh
```

Open the CloudFront address the script printed to check the page right away. Then try
https://k12.ordevista.com/ once DNS has spread (minutes to a few hours).

### Bluehost pitfalls

- **Host Record gets only the part before `.ordevista.com`.** Bluehost adds the domain
  itself. Typing `k12.ordevista.com` produces `k12.ordevista.com.ordevista.com`, which
  won't work. The script already trims the value for you.
- **No trailing dot, and no `https://`** in Points To.
- **Never delete record 1.** AWS uses it to renew the certificate automatically every year.
  If it's removed, the site's HTTPS expires about 13 months later.
- Don't add an A record for `k12`; a hostname can't have both a CNAME and an A record.
- No CAA records exist on ordevista.com today, so nothing blocks AWS from issuing the
  certificate. If you ever add CAA records, include `0 issue "amazon.com"`.

### Check DNS without installing anything

Open these in a browser. Look for an `"Answer"` section that contains your value.

- Validation record: `https://dns.google/resolve?name=<Host from step 1>.ordevista.com&type=CNAME`
- Site record: https://dns.google/resolve?name=k12.ordevista.com&type=CNAME

### If the stack stalls or fails

- If the certificate is still pending after about an hour, recheck record 1 for typos
  and for a doubled `.ordevista.com`.
- If the stack rolls back, fix the record and run `./deploy-infra.sh` again. A new
  certificate means a **new** validation record, so replace the old one in Bluehost.

## Site icon

The browser-tab and phone home-screen icons are the round Ordevista logo from ordevista.com:
`favicon.ico` (16/32/48), `favicon-32.png`, `icon-192.png`, and `apple-touch-icon.png`
(on white, because iOS fills transparent areas with black). To change them, replace those
files in `content/assets/` and run `./publish.sh`. Browsers cache favicons hard, so a
private window shows the new icon right away.

## Adding a resource (the routine)

1. Copy the PDF into `content/files/` (use short, lowercase, dashed names).
2. Add an entry to the right section in `content/resources.json`:
   ```json
   { "title": "MAEDS #62 — slides", "description": "One line on why it matters.",
     "file": "maeds-2026-10-slides.pdf", "type": "PDF", "date": "2026-10-29" }
   ```
   Use `"url"` instead of `"file"` for external links. Optional: `owner`, `logo`, `domain`,
   `badge`, `expires` (YYYY-MM-DD), `featured`.
3. Run `./publish.sh` (add `--strict` to stop if a listed file is missing).

Built-in behavior:
- A listed `file` that isn't in `content/files/` shows as **Coming soon** (no broken links).
- An item past its `expires` date shows as **Closed** with no link. This happens on the next
  publish, so run `./publish.sh` on Nov 1 to close the self-assessment card.
- Need a dedicated page for one event later? Add `content/pages/maeds-2026/index.html`;
  `k12.ordevista.com/maeds-2026` works automatically.

## Privacy and security posture

- No cookies, analytics, fonts, or scripts from third parties; the CSP blocks them anyway.
- The bucket is not public; it denies non-HTTPS access and only CloudFront can read it.
- Versioning keeps 90 days of prior versions, so an accidental overwrite can be undone.
- Access logging is off by default (fewer visitor records to manage). If you want visit
  counts later, CloudFront standard logs can be added without changing the page.

## Cost (estimate)

At conference-handout traffic this stays within or near the AWS free tier: S3 storage of a
few MB, CloudFront requests and transfer, DNS stays at Bluehost (no Route 53 charge), and the ACM certificate is free.

## Before you print the sticky notes

- Visit the live URL on a phone over cellular, not just on Wi-Fi.
- Generate the QR code from the final URL and test it with two phone camera apps.
