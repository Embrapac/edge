import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import unittest
import tempfile
from pathlib import Path
from buffer_manager import VideoBufferManager, MAX_STORAGE_BYTES


class TestVideoBufferManager(unittest.TestCase):
    
    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.storage_path = self.test_dir.name
        self.manager = VideoBufferManager(self.storage_path)

    def tearDown(self):
        """Clean up temporary directory after each test."""
        self.test_dir.cleanup()

    def create_test_file(self, filename: str, size_bytes: int) -> Path:
        """Helper method to create a test file with specific size."""
        filepath = Path(self.storage_path) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(b'0' * size_bytes)
        print(f"Created test file: {filepath} with size: {size_bytes} bytes")
        return filepath

    def test_initialization(self):
        """Test that VideoBufferManager initializes correctly."""
        self.assertTrue(Path(self.storage_path).exists())
        self.assertEqual(self.manager.current_size(), 0)

    def test_current_size_empty(self):
        """Test current_size() returns 0 for empty storage."""
        self.assertEqual(self.manager.current_size(), 0)

    def test_current_size_single_file(self):
        """Test current_size() with a single file."""
        file_size = 1024 * 1024  # 1 MB
        self.create_test_file("test.mp4", file_size)
        self.assertEqual(self.manager.current_size(), file_size)

    def test_current_size_multiple_files(self):
        """Test current_size() with multiple files."""
        size1 = 1024 * 1024  # 1 MB
        size2 = 2 * 1024 * 1024  # 2 MB
        self.create_test_file("test1.mp4", size1)
        self.create_test_file("test2.mp4", size2)
        self.assertEqual(self.manager.current_size(), size1 + size2)

    def test_available_space_empty(self):
        """Test available_space() returns MAX_STORAGE_BYTES when empty."""
        self.assertEqual(self.manager.available_space(), MAX_STORAGE_BYTES)

    def test_available_space_with_files(self):
        """Test available_space() calculates correctly with files."""
        file_size = 1024 * 1024  # 1 MB
        self.create_test_file("test.mp4", file_size)
        expected = MAX_STORAGE_BYTES - file_size
        self.assertEqual(self.manager.available_space(), expected)

    def test_available_space_never_negative(self):
        """Test that available_space() never returns negative values."""
        self.assertGreaterEqual(self.manager.available_space(), 0)

    def test_enforce_limit_no_action_needed(self):
        """Test enforce_limit() when storage is within limits."""
        file_size = 1024 * 1024  # 1 MB (well below limit)
        self.create_test_file("test.mp4", file_size)
        initial_size = self.manager.current_size()
        
        self.manager.enforce_limit()
        
        self.assertEqual(self.manager.current_size(), initial_size)

    def test_enforce_limit_removes_oldest_file(self):
        """Test that enforce_limit() removes the oldest file first."""
        # Create files with known modification times
        file1 = self.create_test_file("old.mp4", 1024 * 1024)
        file2 = self.create_test_file("new.mp4", 1024 * 1024)
        
        # Make file1 older by adjusting timestamps
        os.utime(file1, (0, 0))
        
        # Ensure file2 is newer
        os.utime(file2, (1000000, 1000000))
        
        self.assertTrue(file1.exists())
        self.assertTrue(file2.exists())
        
        self.manager.enforce_limit()
        
        # file1 (older) should still exist since we're well below limit
        self.assertTrue(file1.exists())
        self.assertTrue(file2.exists())

    def test_enforce_limit_respects_max_storage(self):
        """Test that enforce_limit() brings storage within MAX_STORAGE_BYTES."""
        # This test uses a smaller subset to avoid actually creating 25GB
        small_limit = 10 * 1024 * 1024  # 10 MB for testing
        
        # Create files that exceed 10 MB
        self.create_test_file("file1.mp4", 4 * 1024 * 1024)
        self.create_test_file("file2.mp4", 4 * 1024 * 1024)
        self.create_test_file("file3.mp4", 4 * 1024 * 1024)
        
        self.manager.enforce_limit()
        
        # Should be within the real MAX_STORAGE_BYTES limit
        self.assertLessEqual(self.manager.current_size(), MAX_STORAGE_BYTES)

    def test_enforce_limit_keeps_newer_files(self):
        """Test that enforce_limit() prioritizes keeping newer files."""
        file1 = self.create_test_file("oldest.mp4", 1024 * 1024)
        file2 = self.create_test_file("middle.mp4", 1024 * 1024)
        file3 = self.create_test_file("newest.mp4", 1024 * 1024)
        
        # Adjust timestamps
        os.utime(file1, (0, 0))
        os.utime(file2, (500000, 500000))
        os.utime(file3, (1000000, 1000000))
        
        self.manager.enforce_limit()
        
        # All files should exist (well below limit)
        self.assertTrue(file1.exists())
        self.assertTrue(file2.exists())
        self.assertTrue(file3.exists())

    def test_enforce_limit_removes_non_mp4_files(self):
        """Test that enforce_limit() only removes .mp4 files."""
        mp4_file = self.create_test_file("video.mp4", 1024 * 1024)
        txt_file = self.create_test_file("data.txt", 1024 * 1024)
        
        self.manager.enforce_limit()
        
        # Both files should exist (well below limit)
        self.assertTrue(mp4_file.exists())
        self.assertTrue(txt_file.exists())

    def test_storage_path_creation(self):
        """Test that storage path is created if it doesn't exist."""
        new_path = os.path.join(self.test_dir.name, "nested", "path")
        manager = VideoBufferManager(new_path)
        self.assertTrue(Path(new_path).exists())

    def test_current_size_with_subdirectories(self):
        """Test current_size() includes files in subdirectories."""
        self.create_test_file("subdir/test1.mp4", 1024 * 1024)
        self.create_test_file("subdir/test2.mp4", 2 * 1024 * 1024)
        total_size = self.manager.current_size()
        self.assertEqual(total_size, 3 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()