# Dataiku Adobe Analytics plugin

## How to install

### On Adobe Analytics' side

1. Find the global company ID for your account, as explained on [Adobe documentation](https://experienceleague.adobe.com/en/docs/analytics/admin/admin-tools/company-settings/web-services-admin)
2. [Get an Adobe Analytic API key](https://developer.adobe.com/express/embed-sdk/docs/guides/quickstart/)
3. [Create a client ID and client secret](https://helpx.adobe.com/sign/kb/how-to-create-client-id-and-client-secret-adobe-sign.html)

### On Dataiku DSS side

As a Dataiku DSS admin:
- Create a preset, by clicking on **Other sections** > **Plugins** > **Installed** > **Adobe Analytics** > **Settings** > **SSO User accounts** > **+ Add preset**.
- Name the preset, add the client ID and client secret produced on step 3
- Add the company ID retrieved on step 1
- Add the API key produced on step 2

### On Dataiku for each DSS user account

Each DSS user that needs access to Adobe Analytics data will have to go through the Single Sign On using the preset created in the previous section. To do so, the user has to go to their profile page > **Credentials** > **Adobe analytics << preset name >> **> **Connect**

## How to use

In a Dataiku flow, add a dataset + Dataset > Plugins > Adobe Analytics > Get Reports

Select **Single Sign On** type authentication, the preset from section 2.

Press **Test & Get Schema**
