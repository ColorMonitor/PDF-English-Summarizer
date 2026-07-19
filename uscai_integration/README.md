# USC AI integration

Adds the locked project-PDF summarizer to the existing USC Django site. The model remains on Beam; no model files are copied to aaPanel.

## Server requirements

- Existing project: `/www/wwwroot/uscai`
- Existing CA bundle: `/www/wwwroot/uscai/certs/unionsupremecourt-ca-bundle.pem`
- Environment variables in the aaPanel Python project:
  - `BEAM_ENDPOINT_URL=https://kls-pdf-summarizer-810c73b-v1.app.beam.cloud`
  - `BEAM_API_TOKEN=<Beam API token>`
  - `USC_PDF_CA_BUNDLE=/www/wwwroot/uscai/certs/unionsupremecourt-ca-bundle.pem`

Keep `BEAM_API_TOKEN` out of files, Git, screenshots, and terminal history. Add it through aaPanel's environment-variable UI.

## Deploy

Run one command per line in aaPanel Terminal:

```bash
cd /tmp
git clone --depth 1 https://github.com/ColorMonitor/PDF-English-Summarizer.git kls-pdf-summarizer
cd /tmp/kls-pdf-summarizer/uscai_integration
bash deploy.sh /www/wwwroot/uscai
```

Then set the three environment variables above and restart the existing USC Python project from aaPanel.

Test:

```text
https://uscai.koneloneshin.com/publications/projects/18/
```

The project page should show `Summarize` beside `English PDF`.

## Roll back

The deploy script prints its timestamped backup path. Restore its three files, remove the five added integration files, run `collectstatic`, then restart the USC Python project.
