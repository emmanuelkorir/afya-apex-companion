import asyncio

## To test uv run python -m tests.test_login

from app.emr_client.client import EMRClient


async def main():
    client = EMRClient(headless=False)

    try:
        await client.connect()
        await client.save_session()

        print("Login successful!")

        input("Press Enter to close the browser...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())