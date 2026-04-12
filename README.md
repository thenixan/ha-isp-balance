# ISP Balance for Home Assistant

Custom Home Assistant integration that fetches and displays your ISP account balance by scraping the provider's billing portal.

## Supported Providers

| Provider | Billing System | Portal URL |
|----------|---------------|------------|
| NTS Center | LbWeb | `stat.nts.center/lbweb-client/` |
| Parus Telecom | LbWeb | `cabinet.parustelecom.ru` |

Both providers use the same [LbWeb](https://www.lanbilling.ru/) billing platform — only the portal URLs differ.

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
            └── lbweb.py
```

Restart Home Assistant after copying.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **ISP Balance**
3. Select your provider (NTS Center or Parus Telecom)
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

## Adding a New LbWeb Provider

All LbWeb-based ISPs share the same authentication flow and page structure. To add a new one:

1. Add a variant to `ProviderId` in `const.py`:
   ```python
   class ProviderId(StrEnum):
       NTS_CENTER = "nts_center"
       PARUS_TELECOM = "parus_telecom"
       MY_NEW_ISP = "my_new_isp"  # <-- add this
   ```

2. Add the display name to `PROVIDER_DISPLAY_NAMES` in `const.py`:
   ```python
   PROVIDER_DISPLAY_NAMES: dict[ProviderId, str] = {
       ...
       ProviderId.MY_NEW_ISP: "My New ISP",
   }
   ```

3. Add the endpoints to `_LBWEB_ENDPOINTS` in `providers/__init__.py`:
   ```python
   ProviderId.MY_NEW_ISP: LbWebEndpoints(
       sign_in="https://billing.myisp.com/site/login",
       dashboard="https://billing.myisp.com/account/index",
   ),
   ```

No new files or classes needed — all LbWeb portals use identical selectors and auth flow.

## License

MIT
