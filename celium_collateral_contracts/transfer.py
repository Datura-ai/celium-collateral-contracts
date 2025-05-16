from substrateinterface import SubstrateInterface, Keypair

substrate = SubstrateInterface(
    url="ws://127.0.0.1:9944",
    # ss58_format=42,
    type_registry_preset='substrate-node-template'
)

# Use Alice (pre-funded dev account)
keypair = Keypair.create_from_uri("//alice")

# Destination keypair
to_address = "5Hi5yqEpcPgVqoXwZnDeFmczdtyVvQBj17aG3NCJgDpDzi1Z"

call = substrate.compose_call(
    call_module="Tao",
    call_function="transfer",
    call_params={"dest": to_address, "value": 10**12}  # 1 TAO
)

extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

print(f"Sent: {receipt.extrinsic_hash}")