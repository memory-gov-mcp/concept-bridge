# 可选别名。规范命令是 `uv run task <cmd>`，Windows 与 Linux 相同。
# 有 GNU make 时，这些目标与 task 命令一一对应。

.PHONY: setup contract check e2e eval dev demo freeze

setup:
	uv run task setup

contract:
	uv run task contract

check:
	uv run task check

e2e:
	uv run task e2e

eval:
	uv run task eval

dev:
	uv run task dev

demo:
	uv run task demo

freeze:
	uv run task freeze $(TAG)
