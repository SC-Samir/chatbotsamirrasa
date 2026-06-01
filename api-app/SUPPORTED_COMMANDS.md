# Supported Commands (`ws.v2`)

All commands return the stable `ws.v2` envelope:
- `event_type`
- `status`
- `action_id`
- `human_message`
- `structured_payload`
- `next_actions`
- `risk_level`

Destructive commands require `confirm <token>`.
All mutating commands include an `Action preview` in `human_message` and `structured_payload.preview`.

## App
- `apps.list` (requires: `region`)
- `apps.get` (requires: `app_name`, `region`)
- `apps.create` (requires: `app_name`, `region`)
- `apps.restart` (requires: `app_name`, `region`)
- `apps.set_force_https` (requires: `app_name`, `region`, `enabled`)
- `apps.set_router_logs` (requires: `app_name`, `region`, `enabled`)
- `apps.set_sticky_session` (requires: `app_name`, `region`, `enabled`)
- `apps.change_project` (requires: `app_name`, `region`, `project_id`)

## Deployments
- `deployments.list`
- `deployments.details` (requires: `deployment_id`)
- `deployments.output` (requires: `deployment_id`)
- `deployments.create` (requires: `github_repo` or `source_url`)
- `deployments.rollback` (requires: `release_id`)
- `deployments.cache_reset` (destructive, confirmation required)

## Containers and Scaling
- `containers.list`
- `containers.scale` (requires: `container_type`, `amount`)
- `containers.stop` (destructive, confirmation required)
- `containers.signal` (destructive, confirmation required)
- `autoscalers.list`
- `autoscalers.create` (requires: `container_type`, `min_containers`, `max_containers`, `metric`, `target`)
- `autoscalers.update` (requires: `autoscaler_id`)
- `autoscalers.delete` (destructive, confirmation required)

## Environment and Addons
- `env_vars.list`
- `env_vars.set` (requires: `env_name`, `env_value`)
- `env_vars.unset` (destructive, confirmation required)
- `addons.list`
- `addons.add` (requires: `addon_id`)
- `addons.remove` (destructive, confirmation required)

## Domains, Collaborators, Logging, Notifiers
- `domains.list`
- `domains.create` (requires: `domain`)
- `domains.delete` (destructive, confirmation required)
- `collaborators.list`
- `collaborators.invite` (requires: `email`)
- `collaborators.update_role` (requires: `collaborator_id`, `is_limited`)
- `collaborators.delete` (destructive, confirmation required)
- `log_drains.list`
- `log_drains.create` (requires: `drain_type`)
- `log_drains.delete` (destructive, confirmation required)
- `notifiers.list`
- `notifiers.create` (requires: `notifier_name`, `platform_id`)
- `notifiers.update` (requires: `notifier_id`)
- `notifiers.delete` (destructive, confirmation required)

## Other
- `events.list`
- `projects.list` (requires: `region`)
- `memory.show`
- `memory.forget` (requires: `memory_key`)
- `memory.pin` (requires: `memory_key`)
- `one_off.run` (requires: `command`)
- `confirm` (requires: `confirm_token`)
