from agents import QbittorrentAgent
import asyncio

if __name__ == "__main__":
    task = "下载电影: Before sunrise"
    asyncio.run(QbittorrentAgent(task).run())
