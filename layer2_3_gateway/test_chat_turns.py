import asyncio
import json
from app.services.llm_extractor import LLMExtractorService
from app.schemas.trip import LLMDataContract

async def main():
    service = LLMExtractorService()
    
    # Turn 1: "Đại Nội, cafe muối, ăn chay"
    print("--- TURN 1 ---")
    msg1 = "Đại Nội, cafe muối, ăn chay"
    history1 = []
    contract1 = LLMDataContract()
    
    res1 = await service.process_chat_turn(msg1, history1, contract1)
    print(f"Reply: {res1['reply']}")
    print(f"Status: {res1['status']}")
    print(f"Missing fields: {res1['missing_fields']}")
    print(f"Updated Contract Locked POIs: {res1['updated_contract'].locked_pois}")
    print(f"Updated Contract Destination: {res1['updated_contract'].destination}")
    print(f"Updated Contract Tags: {res1['updated_contract'].tags}")
    print(f"Updated Contract Food Prefs: {res1['updated_contract'].food_preferences}")
    
    # Turn 2: "Huế"
    print("\n--- TURN 2 ---")
    msg2 = "Huế"
    # Reconstruct history list as the web UI would map it:
    history2 = [
        {"role": "user", "content": msg1},
        {"role": "assistant", "content": res1["reply"]}
    ]
    contract2 = res1["updated_contract"]
    
    res2 = await service.process_chat_turn(msg2, history2, contract2)
    print(f"Reply: {res2['reply']}")
    print(f"Status: {res2['status']}")
    print(f"Missing fields: {res2['missing_fields']}")
    print(f"Updated Contract Locked POIs: {res2['updated_contract'].locked_pois}")
    print(f"Updated Contract Destination: {res2['updated_contract'].destination}")
    print(f"Updated Contract Tags: {res2['updated_contract'].tags}")
    print(f"Updated Contract Food Prefs: {res2['updated_contract'].food_preferences}")

    # Turn 3: "2 triệu"
    print("\n--- TURN 3 ---")
    msg3 = "2 triệu"
    history3 = history2 + [
        {"role": "user", "content": msg2},
        {"role": "assistant", "content": res2["reply"]}
    ]
    contract3 = res2["updated_contract"]
    
    res3 = await service.process_chat_turn(msg3, history3, contract3)
    print(f"Reply: {res3['reply']}")
    print(f"Status: {res3['status']}")
    print(f"Missing fields: {res3['missing_fields']}")
    print(f"Updated Contract Locked POIs: {res3['updated_contract'].locked_pois}")
    print(f"Updated Contract Destination: {res3['updated_contract'].destination}")
    print(f"Updated Contract Tags: {res3['updated_contract'].tags}")
    print(f"Updated Contract Food Prefs: {res3['updated_contract'].food_preferences}")

if __name__ == "__main__":
    asyncio.run(main())
