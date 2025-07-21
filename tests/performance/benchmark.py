#!/usr/bin/env python3
"""
Performance Benchmarking Script
"""
import time
import statistics
import json
import requests
import concurrent.futures
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


class ServeMLBenchmark:
    """Performance benchmark for ServeML platform"""
    
    def __init__(self, base_url="http://localhost:8000", output_dir="benchmark_results"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
    
    def measure_endpoint(self, method, endpoint, data=None, files=None, headers=None, iterations=100):
        """Measure endpoint performance"""
        times = []
        errors = 0
        
        for _ in range(iterations):
            start = time.time()
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
                elif method == "POST":
                    if files:
                        response = requests.post(f"{self.base_url}{endpoint}", files=files, data=data, headers=headers)
                    else:
                        response = requests.post(f"{self.base_url}{endpoint}", json=data, headers=headers)
                
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code >= 400:
                    errors += 1
            except Exception as e:
                errors += 1
                print(f"Error: {e}")
        
        return {
            "endpoint": endpoint,
            "method": method,
            "iterations": iterations,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "avg_time": statistics.mean(times) if times else 0,
            "median_time": statistics.median(times) if times else 0,
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": np.percentile(times, 95) if times else 0,
            "p99": np.percentile(times, 99) if times else 0,
            "errors": errors,
            "error_rate": errors / iterations
        }
    
    def benchmark_auth_endpoints(self):
        """Benchmark authentication endpoints"""
        print("Benchmarking authentication endpoints...")
        
        # Register endpoint
        register_data = {
            "email": "bench@test.com",
            "username": "benchuser",
            "password": "benchpass123"
        }
        self.results["register"] = self.measure_endpoint("POST", "/api/v1/auth/register", data=register_data, iterations=50)
        
        # Login endpoint
        login_data = {
            "email": "bench@test.com",
            "password": "benchpass123"
        }
        self.results["login"] = self.measure_endpoint("POST", "/api/v1/auth/login", data=login_data, iterations=100)
        
        # Get token for authenticated requests
        response = requests.post(f"{self.base_url}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Current user endpoint
            self.results["current_user"] = self.measure_endpoint("GET", "/api/v1/auth/me", headers=headers)
    
    def benchmark_deployment_endpoints(self):
        """Benchmark deployment endpoints"""
        print("Benchmarking deployment endpoints...")
        
        # Get auth token
        login_response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
            "email": "bench@test.com",
            "password": "benchpass123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # List deployments
            self.results["list_deployments"] = self.measure_endpoint("GET", "/api/v1/deployments", headers=headers)
            
            # Deploy model (smaller iterations due to file operations)
            with open("test_models/iris_logistic.pkl", "rb") as model_f, \
                 open("test_models/requirements_minimal.txt", "rb") as req_f:
                
                files = {
                    "model_file": ("model.pkl", model_f.read(), "application/octet-stream"),
                    "requirements_file": ("requirements.txt", req_f.read(), "text/plain")
                }
                self.results["deploy_model"] = self.measure_endpoint(
                    "POST", "/api/v1/deploy", 
                    files=files, 
                    headers=headers, 
                    iterations=10
                )
    
    def benchmark_prediction_endpoints(self):
        """Benchmark prediction endpoints"""
        print("Benchmarking prediction endpoints...")
        
        # Assuming we have a deployed model
        test_data = {
            "deployment_id": "test-deployment",
            "data": {"feature1": 5.1, "feature2": 3.5, "feature3": 1.4, "feature4": 0.2}
        }
        
        # Get auth token
        login_response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
            "email": "bench@test.com",
            "password": "benchpass123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            self.results["predict"] = self.measure_endpoint(
                "POST", "/api/v1/test-model",
                data=test_data,
                headers=headers,
                iterations=200
            )
    
    def benchmark_concurrent_requests(self):
        """Benchmark concurrent request handling"""
        print("Benchmarking concurrent requests...")
        
        def make_request():
            start = time.time()
            response = requests.get(f"{self.base_url}/")
            return time.time() - start, response.status_code
        
        concurrent_levels = [1, 5, 10, 20, 50, 100]
        concurrent_results = []
        
        for level in concurrent_levels:
            print(f"Testing {level} concurrent requests...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(make_request) for _ in range(level * 10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            times = [r[0] for r in results]
            errors = sum(1 for r in results if r[1] >= 400)
            
            concurrent_results.append({
                "concurrent_level": level,
                "total_requests": level * 10,
                "avg_time": statistics.mean(times),
                "max_time": max(times),
                "p95": np.percentile(times, 95),
                "errors": errors
            })
        
        self.results["concurrent"] = concurrent_results
    
    def benchmark_file_sizes(self):
        """Benchmark different model file sizes"""
        print("Benchmarking different file sizes...")
        
        file_sizes = [
            ("1MB", 1 * 1024 * 1024),
            ("5MB", 5 * 1024 * 1024),
            ("10MB", 10 * 1024 * 1024),
            ("50MB", 50 * 1024 * 1024),
            ("100MB", 100 * 1024 * 1024),
            ("250MB", 250 * 1024 * 1024)
        ]
        
        # Get auth token
        login_response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
            "email": "bench@test.com",
            "password": "benchpass123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            size_results = []
            
            for size_name, size_bytes in file_sizes:
                print(f"Testing {size_name} file...")
                
                # Create dummy file
                dummy_data = b"0" * size_bytes
                
                files = {
                    "model_file": (f"model_{size_name}.pkl", dummy_data, "application/octet-stream"),
                    "requirements_file": ("requirements.txt", b"numpy==1.24.3", "text/plain")
                }
                
                start = time.time()
                response = requests.post(
                    f"{self.base_url}/api/v1/deploy",
                    files=files,
                    headers=headers
                )
                elapsed = time.time() - start
                
                size_results.append({
                    "size": size_name,
                    "bytes": size_bytes,
                    "time": elapsed,
                    "status": response.status_code,
                    "mb_per_second": (size_bytes / 1024 / 1024) / elapsed if elapsed > 0 else 0
                })
            
            self.results["file_sizes"] = size_results
    
    def generate_plots(self):
        """Generate performance visualization plots"""
        print("Generating performance plots...")
        
        # Endpoint response times
        endpoints = [k for k in self.results.keys() if k not in ["concurrent", "file_sizes"]]
        avg_times = [self.results[k]["avg_time"] for k in endpoints]
        
        plt.figure(figsize=(10, 6))
        plt.bar(endpoints, avg_times)
        plt.xlabel("Endpoint")
        plt.ylabel("Average Response Time (seconds)")
        plt.title("Average Response Times by Endpoint")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / "endpoint_response_times.png")
        plt.close()
        
        # Concurrent request performance
        if "concurrent" in self.results:
            concurrent_data = self.results["concurrent"]
            levels = [d["concurrent_level"] for d in concurrent_data]
            avg_times = [d["avg_time"] for d in concurrent_data]
            
            plt.figure(figsize=(10, 6))
            plt.plot(levels, avg_times, marker='o')
            plt.xlabel("Concurrent Requests")
            plt.ylabel("Average Response Time (seconds)")
            plt.title("Performance Under Concurrent Load")
            plt.grid(True)
            plt.savefig(self.output_dir / "concurrent_performance.png")
            plt.close()
        
        # File size upload performance
        if "file_sizes" in self.results:
            size_data = self.results["file_sizes"]
            sizes = [d["size"] for d in size_data]
            upload_speeds = [d["mb_per_second"] for d in size_data]
            
            plt.figure(figsize=(10, 6))
            plt.bar(sizes, upload_speeds)
            plt.xlabel("File Size")
            plt.ylabel("Upload Speed (MB/s)")
            plt.title("Upload Speed by File Size")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(self.output_dir / "upload_speeds.png")
            plt.close()
    
    def save_results(self):
        """Save benchmark results to JSON"""
        with open(self.output_dir / "benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate summary report
        with open(self.output_dir / "benchmark_summary.txt", "w") as f:
            f.write("ServeML Performance Benchmark Summary\n")
            f.write("=" * 50 + "\n\n")
            
            for endpoint, metrics in self.results.items():
                if endpoint in ["concurrent", "file_sizes"]:
                    continue
                
                f.write(f"{endpoint}:\n")
                f.write(f"  Average time: {metrics['avg_time']:.3f}s\n")
                f.write(f"  Median time: {metrics['median_time']:.3f}s\n")
                f.write(f"  95th percentile: {metrics['p95']:.3f}s\n")
                f.write(f"  99th percentile: {metrics['p99']:.3f}s\n")
                f.write(f"  Error rate: {metrics['error_rate']:.1%}\n")
                f.write("\n")
    
    def run_all_benchmarks(self):
        """Run all benchmarks"""
        print("Starting ServeML performance benchmarks...")
        print("-" * 50)
        
        self.benchmark_auth_endpoints()
        self.benchmark_deployment_endpoints()
        self.benchmark_prediction_endpoints()
        self.benchmark_concurrent_requests()
        self.benchmark_file_sizes()
        
        self.generate_plots()
        self.save_results()
        
        print("-" * 50)
        print(f"✅ Benchmarks complete! Results saved to {self.output_dir}/")


if __name__ == "__main__":
    benchmark = ServeMLBenchmark()
    benchmark.run_all_benchmarks()