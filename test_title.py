import asyncio
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as M,
)

async def main():
    try:
        mgr = await M.request_async()
        sessions = mgr.get_sessions()
        print(f"Found {len(sessions)} session(s)")
        for i, s in enumerate(sessions):
            info = await s.try_get_media_properties_async()
            print(f"  [{i}] source={s.source_app_user_model_id}")
            print(f"       title={info.title}")
            print(f"       artist={info.artist}")
        current = mgr.get_current_session()
        if current:
            info = await current.try_get_media_properties_async()
            print(f"\nCurrent session:")
            print(f"  source={current.source_app_user_model_id}")
            print(f"  title={info.title}")
            print(f"  artist={info.artist}")
        else:
            print("\nNo current session")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(main())