# Microsoft Store publishing

DevSnapshot uses an MSIX package for Microsoft Store submission. This route lets
Microsoft sign and host the certified package; a purchased Authenticode certificate
is not required for a Store-only MSIX release.

## 1. Reserve the product

In Partner Center, open **Apps and games**, select **New product**, then select
**MSIX or PWA app**. Check and reserve the name **DevSnapshot**.

Reserving a product creates a Partner Center record. Confirm the account and name
before selecting **Reserve product name**.

## 2. Copy the Store identity

Open the reserved product, expand **Product management**, and select
**Product identity**. Copy these three values exactly; they are case-sensitive:

- Package/Identity/Name
- Package/Identity/Publisher
- Package/Properties/PublisherDisplayName

## 3. Build the MSIX

From PowerShell in the repository root, substitute the three exact Partner Center
values:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_store.ps1 `
  -IdentityName '<Package/Identity/Name>' `
  -Publisher '<Package/Identity/Publisher>' `
  -PublisherDisplayName '<PublisherDisplayName>' `
  -Version '1.0.0.0'
```

The builder creates an isolated temporary Python environment, runs all tests,
creates and smoke-tests a one-folder executable, generates Store assets, builds the
MSIX with the Windows SDK, and cleans its temporary environment. Outputs are under
`dist\store`.

The generated MSIX is intentionally unsigned. Upload it directly to Partner Center,
which signs it after certification. It cannot be sideloaded normally unless it is
signed with a certificate trusted by the test machine.

## 4. Complete the submission

- Pricing and availability: Free; select intended markets.
- Properties: Developer tools or Productivity; desktop only.
- Age ratings: Answer the questionnaire based on the app's actual local-file behavior.
- Packages: Upload `dist\store\DevSnapshot_1.0.0.0_x64.msix`.
- Store listing: Use the copy in [LISTING.md](LISTING.md), upload the generated
  300x300 Store logo, and add at least one clean application screenshot.
- Submission options: Use the certification notes in [LISTING.md](LISTING.md).

Run the Windows App Certification Kit before submitting. Do not click **Submit for
certification** until every listing, privacy, ownership, and market detail has been
reviewed.

For updates, increase one of the first three version components and keep the fourth
component at `0`, for example `1.0.1.0`.
