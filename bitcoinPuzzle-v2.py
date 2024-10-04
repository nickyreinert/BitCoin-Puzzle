from ecdsa import SECP256k1, SigningKey
import binascii
import hashlib
import base58
import time
import psutil
import concurrent.futures

def private_to_public(private_key_bytes):
    private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string("compressed")

def public_key_to_address(compressed_public_key_bytes):
    sha256_hash = hashlib.sha256(compressed_public_key_bytes).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    versioned_payload = b'\x00' + ripemd160_hash
    checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
    payload_with_checksum = versioned_payload + checksum
    return base58.b58encode(payload_with_checksum).decode()

def generate_key(i, target_address):
    
    private_key_hex = '{:064x}'.format(i)
    private_key_bytes = binascii.unhexlify(private_key_hex)
    compressed_public_key = private_to_public(private_key_bytes)
    bitcoin_address = public_key_to_address(compressed_public_key)
    
    if bitcoin_address == target_address:
        return (private_key_hex, compressed_public_key, bitcoin_address)

    return None

def batch_key_generation(start, end, target_address):
    found_key = None
    for i in range(start, end):
        # Generate and check keys within this range
        res = generate_key(i, target_address)
        if res:
            found_key = res
            break
    return found_key

def measure_performance(min_exp, max_exp, target_address, num_workers):
    # Calculate the min and max values from the exponents
    min_val = 2 ** min_exp
    max_val = 2 ** max_exp - 1
    n = max_val - min_val + 1  # Number of iterations (key space size)

    # Start timer and capture initial CPU/memory usage
    process = psutil.Process()
    initial_cpu = psutil.cpu_percent(interval=None)  # CPU usage at start
    initial_memory = process.memory_info().rss / (1024 * 1024)  # Memory in MB

    # Start timing
    start_time = time.time()

    found = None
    total_processed = 0  # Track the total number of keys processed
    last_reported_percent = 0  # Track the last percentage reported

    print(f"Starting parallel processing with {n} iterations...")

    batch_size = n // num_workers  # Assuming you want 12 workers

    # Run the function (e.g., generate_keys)
        # Use concurrent.futures for parallel processing
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_index = {
            executor.submit(batch_key_generation, start, min(start + batch_size, max_val + 1), target_address): start
            for start in range(min_val, max_val + 1, batch_size)
        }

        last_reported_percent = 0
        
        for future in concurrent.futures.as_completed(future_to_index):
            if found:
                break

            i = future_to_index[future]

            res = future.result()

            start_index = future_to_index[future]
            processed_in_batch = min(batch_size, max_val + 1 - start_index)
            total_processed += processed_in_batch

            if res:
                found = res
                print('-' * 80)
                print(f'Private Key (Hex): {res[0]}')
                print(f'Compressed Public Key: {binascii.hexlify(res[1]).decode()}')
                print(f'Bitcoin Address (Base58Check): {res[2]}')
                break  # Break after finding the target to stop other processes

            # Print progress update every 1% of the total iterations
            current_percent = (total_processed * 100) // n
            if current_percent >= last_reported_percent + 10:
                print(f"Processed {total_processed} out of {n} keys ({current_percent}%)...")
                last_reported_percent = current_percent

    # End timing
    end_time = time.time()
    total_time = end_time - start_time
    average_time_per_iteration = (total_time / n) * 1000  # in milliseconds

    # Capture final CPU and memory usage
    final_cpu = psutil.cpu_percent(interval=None)
    final_memory = process.memory_info().rss / (1024 * 1024)  # Memory in MB

    # Print total time taken and average time per iteration
    print(f'Total time taken: {total_time:.6f} seconds')
    print(f'Average time per iteration: {average_time_per_iteration:.3f} ms')

    # Print CPU and memory usage
    print(f'Initial CPU Usage: {initial_cpu}%')
    print(f'Final CPU Usage: {final_cpu}%')
    print(f'Initial Memory Usage: {initial_memory:.2f} MB')
    print(f'Final Memory Usage: {final_memory:.2f} MB')

if __name__ == '__main__':
    target_address = '1HsMJxNiV7TLxmoF6uJNkydxPFDog4NQum'
    num_workers = 12
    measure_performance(19, 20, target_address, num_workers)
