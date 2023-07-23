# HomeAssistant Secret Service 🕴

[![GitHub Release][releases-shield]][releases]
[![HACS Validation][validation-shield]](validation)
[![hacs][hacsbadge]][hacs]

[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A small configurable service that can validate values against secrets without having to expose the secrets to other configurations. Home Assistant made the choice to not allow secrets inside of templates which makes checking a value against a secret in an automation or script difficult. While there are workarounds they are either insecure, rudimentary, inflexible, or some combination of these. With the Secret Service values can be validated against secrets stored in the `secrets.yaml` file or even hard coded into the service configuration.

Secrets are hashed using `bcrypt` with a random salt generated at setup time to ensure as much security as possible and limit where secrets are exposed. Secrets and hashes are not exposed via the service call or stored in the state, again the maintain as much security as possible.

## ✨Features✨
 Name | Description
 -- | --
 Single Secret Validation | Validation against a single named secret.
 Grouped Secret Validation | Validation against one or more secrets with a single name. This can be useful when you want to provide different secrets but validate in a single call. Each group can only have one instance of each secret.

### Planned Features
 Name | Description
 -- | --
Rate Limiting | Configurable limits on how often secrets can be validated against to prevent brute force attacks.
Failure Limits | Configurable limits on how many times a failed validation can occur and options to handle when the limits are reached (eg. lock for a period of time)
Conditions | Allow secrets and groups to have conditions on their use allowing for even greater customization. This assumes that there's a way to use the existing condition system within the integration, more research is needed here.

## 📦Installation📦

### HACS (Recommended)
1. Open HACS
1. Go to _Integrations_
1. Click the ellipse button in the top right and select _Custom Repositories_
1. Enter the following information
    * _Repository_: `https://github.com/amura11/ha-secret-service`
    * _Category_:  `Integration`
1. Click "Add"
1. Close the modal then click _Explore & Download Repositories_
1. Search for `Secret Checker`` and select the repository
1. Click the _Download_ button
1. Restart Home Assistant
1. Add an [entry to your configuration](#main-configuration) for the Secret Service
1. Restart Home Assistant ...again

### Manually
1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `secret_service`.
1. Download _all_ the files from the `custom_components/secret_service/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. Add an [entry to your configuration](#main-configuration) for the Secret Service
1. Restart Home Assistant ...again

## 🔧Configuration🔧

### Main Configuration
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`secrets` | array | An array of [Secret Configurations](#single-secret-configuration) | * |
`groups`  | array | An array of [Group Configurations](#secret-group-configuration) | * |

\*Groups and secrets are not required but you should at least have one otherwise why are you using the service? 🤔

### Single Secret Configuration
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`secret` | string | The name of the secret that will be used when calling the service to validate a value against this secret. | ✔ |
`value` | string | The actual value of the secret. This can be pulled from the `secrets.yaml` file or hard coded. | ✔ |

### Secret Group Configuration
 Name | Type | Description | Required | Default
-- | -- | -- | -- | --
`group` | string | The name of the group that will be used when calling the service to validate a value against this group. | ✔ |
`secrets` | array | An array of [Secret Configurations](#single-secret-configuration) | ✔ |

## 📄Usage📄
Call the service using the parameters described below.

 Name | Type | Description | Required
-- | -- | -- | --
`name` | string | The name of the group or secret that the value should be validated against | ✔ |
`value` | array | An array of [Secret Configurations](#single-secret-configuration) | ✔ |

### Example
```
service: secret_service.check_secret
data:
  name: "group_or_secret_name"
  value: "sEcReTpAsSwOrD"
```

## 🎉Contributions are welcome!🎉

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[releases-shield]: https://img.shields.io/github/release/amura11/ha-secret-service.svg?style=for-the-badge
[releases]: https://github.com/amura11/ha-secret-service/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/amura11/ha-secret-service.svg?style=for-the-badge
[commits]: https://github.com/amura11/ha-secret-service/commits/main
[license-shield]: https://img.shields.io/github/license/amura11/ha-secret-service.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[validation-shield]: https://img.shields.io/github/actions/workflow/status/amura11/ha-secret-service/validate.yml?style=for-the-badge&label=HACS%20Validation
[validation]: https://github.com/amura11/ha-secret-service/actions/workflows/validate.yml