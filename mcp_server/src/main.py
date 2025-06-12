from qbittorrent import MagnetSearchMcpServer, QbittorrentMCPServer
import multiprocessing
from agent_logging import logger


def run_magnet_server():
    MagnetSearchMcpServer().run()
    logger.info("Magnet search server started.")


def run_qbittorrent_server():
    QbittorrentMCPServer().run()
    logger.info("Qbittorrent server started.")


if __name__ == "__main__":
    magnet_process = multiprocessing.Process(target=run_magnet_server)
    qbittorrent_process = multiprocessing.Process(target=run_qbittorrent_server)

    # Start both processes
    magnet_process.start()
    qbittorrent_process.start()

    # Wait for both processes to complete
    magnet_process.join()
    qbittorrent_process.join()
