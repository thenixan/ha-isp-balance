# ISP Balance for Home Assistant

Custom Home Assistant integration that fetches and displays your ISP account balance by scraping the provider's billing portal.

## Supported Providers

| Provider | Billing System | Portal URL |
|----------|---------------|------------|
| NTS Center | LbWeb | `stat.nts.center/lbweb-client/` |
| Parus Telecom | LbWeb | `cabinet.parustelecom.ru` |
| RSI-Net (РамСвязьИнвест) | Joomla | `lk.rsi-net.ru` |

NTS Center and Parus Telecom share the [LbWeb](https://www.lanbilling.ru/) billing platform — only the portal URLs differ. RSI-Net runs a Joomla subscriber cabinet instead, with its own authentication flow and page structure.

## Features

- **Multiple accounts** — add as many provider accounts as you need
- **Automatic polling** — balance is refreshed every ~60 minutes with randomized jitter
- **Re-authentication** — if the session expires, HA prompts you to re-enter your password
- **Sensor attributes** — exposes overdraft, operator name, and portal notifications
- **Localization** — English and Russian UI

## Installation

### HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations** → **...** (top-right menu) → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

Copy `custom_components/isp_balance/` into your Home Assistant config directory:

```
<ha-config>/
└── custom_components/
    └── isp_balance/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        ├── translations/
        │   ├── en.json
        │   └── ru.json
        └── providers/
            ├── __init__.py
            ├── base.py
            ├── common.py
            ├── lbweb.py
            └── rsi.py
```

Restart Home Assistant after copying.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **ISP Balance**
3. Select your provider (NTS Center, Parus Telecom, or RSI-Net)
4. Enter your billing portal login and password
5. The integration validates your credentials against the portal and creates a balance sensor

## Sensor

| Attribute | Description |
|-----------|-------------|
| `state` | Current account balance (numeric, e.g. `1234.56`) |
| `unit_of_measurement` | `RUB` |
| `overdraft` | Credit limit, if available |
| `operator` | Operator / company name |
| `notification` | Portal notification message, if any |

The sensor uses `SensorDeviceClass.MONETARY`, so HA displays it with proper currency formatting and records history for graphing.

RSI-Net additionally exposes what its cabinet publishes:

| Attribute | Example |
|-----------|---------|
| `login` | `v158-197` |
| `blocking` | `Интернет доступен` |
| `tariff` | `1390 руб - 250 Мбит - ЧС-2026` |
| `next_charge_date` | `01.08.2026` |
| `total_cost` | `1 390,00 р.` |

The cabinet also publishes the subscriber's name, address and phone number. These are deliberately **not** exposed — entity attributes are written to the recorder database and visible throughout the UI.

## Adding a New LbWeb Provider

All LbWeb-based ISPs share the same authentication flow and page structure. To add a new one:

1. Add a variant to `ProviderId` in `const.py`:
   ```python
   class ProviderId(StrEnum):
       NTS_CENTER = "nts_center"
       PARUS_TELECOM = "parus_telecom"
       MY_NEW_ISP = "my_new_isp"  # <-- add this
   ```

2. Add the display name to `PROVIDER_DISPLAY_NAMES` and the platform to
   `PROVIDER_BILLING_SYSTEMS` in `const.py`:
   ```python
   PROVIDER_DISPLAY_NAMES: dict[ProviderId, str] = {
       ...
       ProviderId.MY_NEW_ISP: "My New ISP",
   }

   PROVIDER_BILLING_SYSTEMS: dict[ProviderId, str] = {
       ...
       ProviderId.MY_NEW_ISP: "LbWeb",
   }
   ```

3. Add the endpoints to `_LBWEB_ENDPOINTS` in `providers/__init__.py`:
   ```python
   ProviderId.MY_NEW_ISP: LbWebEndpoints(
       sign_in="https://billing.myisp.com/site/login",
       dashboard="https://billing.myisp.com/account/index",
   ),
   ```

4. Add the option label to `strings.json` and both `translations/*.json`.

No new files or classes needed — all LbWeb portals use identical selectors and auth flow.

## Adding a Non-LbWeb Provider

Providers on other billing platforms need their own module implementing the
`ISPProvider` interface from `providers/base.py` — see `providers/rsi.py` for a
worked example. Reusable HTTP and number-parsing helpers live in
`providers/common.py`. Register the new class in `get_provider()` in
`providers/__init__.py`, then follow steps 1, 2, and 4 above.

## License

MIT
