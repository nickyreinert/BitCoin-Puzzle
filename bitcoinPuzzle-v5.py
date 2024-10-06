from ecdsa import SECP256k1, SigningKey
import binascii
import hashlib
import base58
import time
import psutil
import random
import concurrent.futures
from multiprocessing import Manager

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

def batch_key_generation(start, end, target_address, found_flag, lock):
    found_key = None
    for i in range(start, end):
        # Check if another thread/process has already found the key
        if found_flag.value:
            return None  # Exit early if key was found

        # Generate and check keys within this range
        result = generate_key(i, target_address)
        
        # Print for debugging
        # print(f"Generated key for {i}: {result}")

        if result:  # If a key matches the target address
            with lock:  # Acquire the lock before modifying shared state
                if not found_flag.value:  # Double-check if the key wasn't already found
                    # print(f"Key found by process {start} at iteration {i}")
                    found_key = result  # Save the found key
                    found_flag.value = True  # Set the flag to indicate a key was found
                    return found_key  # Return the found key immediately

    return found_key  # Return the found key or None if not found

def divide_into_chunks(start, end, chunk_size):
    """
    Divide the batch (start, end) into smaller chunks of size chunk_size.
    """
    return list(range(start, end, chunk_size))

def measure_performance(min_exp, max_exp, target_address, num_chunks, num_workers=1):
    # Calculate the min and max values from the exponents
    min_val = 2 ** min_exp
    max_val = 2 ** max_exp - 1
    n = max_val - min_val + 1  # Number of iterations (key space size)
    chunk_size = (n // num_workers) // num_chunks  # Calculate chunk size based on number of chunks

    # Start timer and capture initial CPU/memory usage
    process = psutil.Process()
    initial_cpu = psutil.cpu_percent(interval=None)  # CPU usage at start
    initial_memory = process.memory_info().rss / (1024 * 1024)  # Memory in MB

    # Start timing
    start_time = time.time()

    found = None  # Initialize found here

    print(f"Starting parallel processing with {n} iterations...")

    # Cut the entire range into chunks
    all_chunks = divide_into_chunks(min_val, max_val + 1, chunk_size)
    total_chunks = len(all_chunks)

    # Randomize the list of chunks
    random.shuffle(all_chunks)

    chunks_per_batch = (total_chunks + num_workers - 1) // num_workers

    batch_size = n // num_workers

    start_points = list(range(min_val, max_val + 1, batch_size))

    total_chunks = sum(len(divide_into_chunks(start, min(start + batch_size, max_val + 1), chunk_size)) for start in start_points)
    processed_chunks = 0

    # Create a manager to handle shared state
    with Manager() as manager:
        found_flag = manager.Value('i', False)  # Shared flag to signal when key is found
        lock = manager.Lock()  # Shared lock to synchronize access

        # Run the function (e.g., generate_keys) using concurrent.futures for parallel processing
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_index = {}

            for i in range(0, total_chunks, chunks_per_batch):
                batch_chunks = all_chunks[i:i+chunks_per_batch]

                # Divide the batch into smaller chunks
                for chunk_start in batch_chunks:
                    chunk_end = min(chunk_start + chunk_size, max_val + 1)

                    # print(", ".join(f"{chunk:x}" for chunk in chunks[:1]))  # Print first chunk item

                    # Ensure chunk_start is less than chunk_end
                    if chunk_start < chunk_end:
                        future = executor.submit(batch_key_generation, chunk_start, chunk_end, target_address, found_flag, lock)
                        future_to_index[future] = chunk_start  # Store only the start

            last_reported_percent = 0

            for future in concurrent.futures.as_completed(future_to_index):

                result = future.result()  # Get the result of the future

                if result:  # If a result is found (e.g., private key found)
                    with lock:  # Acquire lock for shared state modification
                        found_flag.value = True  # Signal that a key has been found
                        print('-' * 80)
                        print(f'Private Key (Hex): {result[0]}')  # Ensure this is the correct index
                        compressed_public_key_bytes = result[1] if isinstance(result[1], bytes) else result[1].encode()
                        print(f'Compressed Public Key: {binascii.hexlify(compressed_public_key_bytes).decode()}')
                        print(f'Bitcoin Address (Base58Check): {result[2]}')

                    break  # Break after finding the target to stop other processes

                if found:  # Check if we have already found a key
                    break

                # Increment processed chunks
                processed_chunks += 1
                current_percent = (processed_chunks * 100) / total_chunks
                if current_percent >= last_reported_percent + 10:  # Report every 1% increase
                    print(f"Processed {processed_chunks:,} out of {total_chunks:,} chunks ({current_percent:.2f}%)...")
                    last_reported_percent = int(current_percent)

    # Calculate and print the final statistics
    end_time = time.time()
    total_time = end_time - start_time
    final_cpu = psutil.cpu_percent(interval=None)
    final_memory = process.memory_info().rss / (1024 * 1024)  # Memory in MB

    print(f"\nTotal time: {total_time:.2f} seconds")
    print(f"CPU usage increased by: {final_cpu - initial_cpu:.2f}%")
    print(f"Memory usage increased by: {final_memory - initial_memory:.2f} MB")
    
    # Print CPU and memory usage
    print(f'Initial CPU Usage: {initial_cpu}%')
    print(f'Final CPU Usage: {final_cpu}%')
    print(f'Initial Memory Usage: {initial_memory:.2f} MB')
    print(f'Final Memory Usage: {final_memory:.2f} MB')

if __name__ == '__main__':
    target_address = '1HsMJxNiV7TLxmoF6uJNkydxPFDog4NQum'
    num_workers = 12
    num_chunks = 1000
    measure_performance(19, 20, target_address, num_chunks, num_workers)
