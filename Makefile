# 可选别名层。本队机器没有 make，规范命令是 `uv run task <cmd>`。
# 装了 make 的人可以用这些目标，行为完全一致。

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
