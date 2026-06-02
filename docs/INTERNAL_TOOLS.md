# Internal Tools

Mythic began as a complex subcommand-based CLI tool. As it evolved into an interactive coding companion, these legacy commands were preserved and repurposed as **internal tools**.

## Legacy Commands as Machinery

The companion shell is powered by the same battle-tested code that drove the original `mythic` commands. When you ask the interactive shell to "Find the memory subsystem," it translates your intent into an execution of the `mythic scan` machinery.

The old command catalog has been shifted to the `admin` namespace to keep the default `mythic --help` clean and focused on the interactive shell workflow.

## The `admin` Namespace

If you prefer to run legacy commands manually, or need them for CI/CD scripting, they are fully accessible by prefixing them with `admin`:

```bash
mythic admin scan .
mythic admin packet create
mythic admin workflow run .mythic/workflows/deploy.yml
mythic admin patch apply staged.patch
mythic admin reflect
```

By design, **no code was casually deleted** during the transition to an interactive shell. The raw primitives remain available for those who need them, while the typical user interacts safely through the conversation loop.\n