import time
from realestate.batch.complex_aggregate import aggregate_all_sigungu_complex

start = time.time()
aggregate_all_sigungu_complex(["202310", "202311"])
print("Time taken:", time.time() - start)
