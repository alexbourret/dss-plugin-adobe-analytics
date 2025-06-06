# Dataiku Adobe Analytics plugin

This plugin is under developpement. 

## How to install

### On Adobe Analytics' side

1. Find the global company ID for your account, as explained on [Adobe documentation](https://experienceleague.adobe.com/en/docs/analytics/admin/admin-tools/company-settings/web-services-admin)
2. [Get an Adobe Analytic API key](https://developer.adobe.com/analytics-apis/docs/2.0/guides/)
3. [Create a client ID and client secret](https://developer.adobe.com/developer-console/docs/guides/credentials/#oauth-user-authentication)

### On Dataiku DSS side

As a Dataiku DSS admin:
- Install the plugin
    - by going to **Other sections** > **Plugins** > **Add Plugin** > **Fetch from GIT repository** and add **https://github.com/alexbourret/dss-plugin-adobe-analytics** in **Repository URL**, 
    - or update by downloading the latest [zip file from here](https://github.com/alexbourret/dss-plugin-adobe-analytics/releases), then **Other sections** > **Plugins** > **Add Plugin** > **Upload**, make sure **This is an update for an installed plugin** is ticked, and browse to the downloaded zip's path. 
- Create a preset, by clicking on **Other sections** > **Plugins** > **Installed** > **Adobe Analytics** > **Settings** > **SSO User accounts** > **+ Add preset**.
- Name the preset, add the client ID and client secret produced on step 3
- Add the company ID retrieved on step 1
- Add the API key produced on step 2

### On Dataiku for each DSS user account

Each DSS user that needs access to Adobe Analytics data will have to go through the Single Sign On using the preset created in the previous section. To do so, the user has to go to their profile page > **Credentials** > Adobe analytics << preset name >> > **Connect**

## How to use

In a Dataiku flow, add a dataset + Dataset > Plugins > Adobe Analytics > Get Reports

Select **Single Sign On** type authentication, the preset from section 2.

Press **Test & Get Schema**
