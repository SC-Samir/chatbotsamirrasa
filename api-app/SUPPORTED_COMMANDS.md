# Supported Commands (`ws.v2`)

All commands return the stable `ws.v2` envelope:
- `event_type`
- `status`
- `action_id`
- `human_message`
- `structured_payload`
- `next_actions`
- `risk_level`

## App
- `apps.list` (requires: `region`)
- `apps.get` (requires: `app_name`, `region`)
- `apps.set_force_https` (requires: `app_name`, `region`, `enabled`; confirmation required)
- `apps.set_router_logs` (requires: `app_name`, `region`, `enabled`; confirmation required)
- `apps.set_sticky_session` (requires: `app_name`, `region`, `enabled`; confirmation required)
- `apps.change_project` (requires: `app_name`, `region`, `project_id`; confirmation required)

## Deployments
- `deployments.list`
- `deployments.details` (requires: `deployment_id`)
- `deployments.output` (requires: `deployment_id`)
- `deployments.cache_reset` (confirmation required)

## Autoscalers
- `autoscalers.list`
- `autoscalers.create` (requires: `container_type`, `min_containers`, `max_containers`, `metric`, `target`; confirmation required)
- `autoscalers.update` (requires: `autoscaler_id`; confirmation required)
- `autoscalers.delete` (requires: `autoscaler_id`; confirmation required)

## Domains
- `domains.list`
- `domains.create` (requires: `domain`; confirmation required)
- `domains.delete` (requires: `domain`; confirmation required)

## Collaborators
- `collaborators.list`
- `collaborators.invite` (requires: `email`; confirmation required)
- `collaborators.update_role` (requires: `collaborator_id`, `is_limited`; confirmation required)
- `collaborators.delete` (requires: `collaborator_id`; confirmation required)

## Log Drains
- `log_drains.list`
- `log_drains.create` (requires: `drain_type`; confirmation required)
- `log_drains.delete` (requires: `drain_id`; confirmation required)

## Notifiers
- `notifiers.list`
- `notifiers.create` (requires: `notifier_name`, `platform_id`; confirmation required)
- `notifiers.update` (requires: `notifier_id`; confirmation required)
- `notifiers.delete` (requires: `notifier_id`; confirmation required)

## Containers / One-offs
- `one_off.run` (requires: `command`; confirmation required)
- `containers.stop` (requires: `container_id`; confirmation required)
- `containers.signal` (requires: `container_id`, `signal`; confirmation required)

## Other
- `events.list`
- `projects.list` (requires: `region`)
- `memory.show`
- `memory.forget` (requires: `memory_key`)
- `memory.pin` (requires: `memory_key`)
- `confirm` (requires: `confirm_token`)

## Examples
- `"list apps in osc-fr1"` -> `apps.list`
- `"set force https true for my-app in osc-fr1"` -> `apps.set_force_https`
- `"create autoscaler web min 1 max 4 metric cpu target 0.7 on my-app in osc-fr1"` -> `autoscalers.create`
- `"confirm <token>"` -> `confirm`
