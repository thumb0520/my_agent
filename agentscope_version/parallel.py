import time
from typing import Optional, Union

import agentscope
from agentscope.agents import AgentBase
from agentscope.message import Msg


class WebAgent(AgentBase):

    def __init__(self, name):
        super().__init__(name)

    def get_answer(self, content):
        time.sleep(5)
        return f"来自 {self.name} 对于{content} 的答案"

    def reply(self, x: Optional[Union[Msg, list[Msg]]] = None) -> Msg:
        m_content = x.get_text_content()
        return Msg(
            name=self.name,
            role="assistant",
            content=self.get_answer(m_content)
        )


QUERY = "示例查询"
URLS = ["页面_1", "页面_2", "页面_3", "页面_4", "页面_5"]


def init_without_dist():
    return [WebAgent(f"W{i}") for i in range(len(URLS))]


def init_with_dist():
    return [WebAgent(f"W{i}").to_dist() for i in range(len(URLS))]


def run(agents):
    start = time.time()
    results = []
    for i, url in enumerate(URLS):
        results.append(agents[i].reply(
            Msg(
                name="system",
                role="system",
                content={
                    "url": url,
                    "query": QUERY
                }
            )
        ))
    for result in results:
        print(result.content)
    end = time.time()
    return end - start


if __name__ == "__main__":
    agentscope.init()
    start = time.time()
    simple_agents = init_without_dist()
    dist_agents = init_with_dist()
    end = time.time()
    print(f"初始化时间：{end - start}")
    print(f"无分布式模式下的运行时间：{run(simple_agents)}")
    print(f"分布式模式下的运行时间：{run(dist_agents)}")
