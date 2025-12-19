#!/usr/bin/env python3
"""
Backend API Testing for Prescription OCR Application
Tests all endpoints: upload, get prescription, get all prescriptions
"""

import requests
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from PIL import Image
import io

class PrescriptionOCRTester:
    def __init__(self):
        # Use BACKEND_URL from environment or default to localhost
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        self.base_url = backend_url.rstrip('/') + "/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_prescription_id = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def create_test_image(self):
        """Create a simple test image for upload"""
        # Create a simple white image with text
        img = Image.new('RGB', (400, 300), color='white')
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'N/A')}"
            return self.log_test("Root Endpoint", success, details)
        except Exception as e:
            return self.log_test("Root Endpoint", False, f"Error: {str(e)}")

    def test_upload_prescription(self):
        """Test prescription upload endpoint"""
        try:
            # Create test image
            image_data = self.create_test_image()
            
            # Prepare multipart form data
            files = {
                'file': ('test_prescription.png', image_data, 'image/png')
            }
            
            response = requests.post(
                f"{self.base_url}/upload-prescription",
                files=files,
                timeout=30
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                self.uploaded_prescription_id = data.get('id')
                details += f", ID: {self.uploaded_prescription_id}, Status: {data.get('status')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            return self.log_test("Upload Prescription", success, details)
        except Exception as e:
            return self.log_test("Upload Prescription", False, f"Error: {str(e)}")

    def test_upload_validation(self):
        """Test upload validation (file size, type)"""
        try:
            # Test with non-image file
            files = {
                'file': ('test.txt', b'This is not an image', 'text/plain')
            }
            
            response = requests.post(
                f"{self.base_url}/upload-prescription",
                files=files,
                timeout=10
            )
            
            # Should fail with 400
            success = response.status_code == 400
            details = f"Status: {response.status_code}"
            
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    pass
            
            return self.log_test("Upload Validation (File Type)", success, details)
        except Exception as e:
            return self.log_test("Upload Validation (File Type)", False, f"Error: {str(e)}")

    def test_get_prescription(self):
        """Test getting a specific prescription"""
        if not self.uploaded_prescription_id:
            return self.log_test("Get Prescription", False, "No prescription ID available")
        
        try:
            response = requests.get(
                f"{self.base_url}/prescriptions/{self.uploaded_prescription_id}",
                timeout=10
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Status: {data.get('processing_status')}, Filename: {data.get('filename')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            return self.log_test("Get Prescription", success, details)
        except Exception as e:
            return self.log_test("Get Prescription", False, f"Error: {str(e)}")

    def test_get_all_prescriptions(self):
        """Test getting all prescriptions"""
        try:
            response = requests.get(f"{self.base_url}/prescriptions", timeout=10)
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Count: {len(data)} prescriptions"
                if len(data) > 0:
                    details += f", First item status: {data[0].get('processing_status')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            return self.log_test("Get All Prescriptions", success, details)
        except Exception as e:
            return self.log_test("Get All Prescriptions", False, f"Error: {str(e)}")

    def test_prescription_processing(self):
        """Test prescription processing by waiting and checking status"""
        if not self.uploaded_prescription_id:
            return self.log_test("Prescription Processing", False, "No prescription ID available")
        
        try:
            print("⏳ Waiting for prescription processing (up to 30 seconds)...")
            
            for attempt in range(10):  # Check for 30 seconds
                time.sleep(3)
                
                response = requests.get(
                    f"{self.base_url}/prescriptions/{self.uploaded_prescription_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('processing_status')
                    print(f"   Attempt {attempt + 1}: Status = {status}")
                    
                    if status == 'completed':
                        structured_data = data.get('structured_data')
                        raw_text = data.get('raw_text')
                        details = f"Status: {status}"
                        if structured_data:
                            details += f", Extracted fields: {len([k for k, v in structured_data.items() if v])}"
                        if raw_text:
                            details += f", Raw text length: {len(raw_text)}"
                        return self.log_test("Prescription Processing", True, details)
                    elif status == 'failed':
                        error_msg = data.get('error_message', 'Unknown error')
                        return self.log_test("Prescription Processing", False, f"Processing failed: {error_msg}")
                else:
                    return self.log_test("Prescription Processing", False, f"API error: {response.status_code}")
            
            # Timeout
            return self.log_test("Prescription Processing", False, "Processing timeout (30 seconds)")
            
        except Exception as e:
            return self.log_test("Prescription Processing", False, f"Error: {str(e)}")

    def test_nonexistent_prescription(self):
        """Test getting a non-existent prescription"""
        try:
            fake_id = "nonexistent-id-12345"
            response = requests.get(
                f"{self.base_url}/prescriptions/{fake_id}",
                timeout=10
            )
            
            # Should return 404
            success = response.status_code == 404
            details = f"Status: {response.status_code}"
            
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    pass
            
            return self.log_test("Nonexistent Prescription", success, details)
        except Exception as e:
            return self.log_test("Nonexistent Prescription", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Prescription OCR Backend API Tests")
        print(f"📍 Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        self.test_root_endpoint()
        self.test_upload_validation()
        self.test_upload_prescription()
        self.test_get_prescription()
        self.test_get_all_prescriptions()
        self.test_prescription_processing()
        self.test_nonexistent_prescription()
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All backend tests passed!")
            return 0
        else:
            print("⚠️  Some backend tests failed!")
            return 1

def main():
    tester = PrescriptionOCRTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())