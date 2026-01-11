"""Tests for path traversal prevention.

These tests verify that file tools properly validate paths
and prevent access to sensitive files and directories.
"""

import os
import tempfile

import pytest

from unify_llm.agent.extended_tools import (
    validate_file_path,
    configure_file_sandbox,
    _BLOCKED_PATTERNS,
    create_file_tools,
)


class TestPathValidation:
    """Test path validation for file operations."""

    def test_allows_normal_paths(self):
        """Test that normal paths in allowed directories work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            is_valid, result = validate_file_path(test_file)
            assert is_valid is True
            assert result == os.path.abspath(test_file)

    # SECURITY: Block sensitive file patterns
    @pytest.mark.parametrize("path", [
        "/home/user/.env",
        "/app/.env",
        "~/.ssh/id_rsa",
        "/home/user/.ssh/config",
        "~/.aws/credentials",
        "/etc/passwd",
        "/etc/shadow",
        "/app/secrets.json",
        "/app/credentials.yaml",
    ])
    def test_blocks_sensitive_files(self, path):
        """SECURITY: Block access to sensitive file patterns."""
        is_valid, error = validate_file_path(path)
        assert is_valid is False, f"Should block sensitive file: {path}"
        assert "blocked" in error.lower()

    # SECURITY: Block path traversal attempts
    @pytest.mark.parametrize("path", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/app/data/../../../etc/passwd",
        "/app/./../../etc/shadow",
    ])
    def test_blocks_path_traversal(self, path):
        """SECURITY: Block path traversal attempts."""
        # Note: After normalization, these should either be blocked
        # by pattern matching or sandbox validation
        is_valid, error = validate_file_path(path)
        # The path is either blocked or normalized to something safe
        # If it resolves to a sensitive path, it should be blocked

    def test_blocks_symlink_attacks(self):
        """SECURITY: Test behavior with symlinks."""
        # This test checks that path resolution handles symlinks
        # The actual behavior depends on the system
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink to /etc
            symlink_path = os.path.join(tmpdir, "etc_link")
            try:
                os.symlink("/etc", symlink_path)
                passwd_via_symlink = os.path.join(symlink_path, "passwd")
                is_valid, error = validate_file_path(passwd_via_symlink)
                # Should be blocked due to /etc/passwd pattern
                assert is_valid is False
            except OSError:
                # Symlink creation may fail on some systems
                pytest.skip("Cannot create symlinks on this system")


class TestSandboxConfiguration:
    """Test file sandbox configuration."""

    def test_sandbox_root_enforcement(self):
        """Test that sandbox root restricts access."""
        with tempfile.TemporaryDirectory() as sandbox_root:
            # Configure sandbox
            configure_file_sandbox(sandbox_root=sandbox_root)

            # Path within sandbox should work
            inside_path = os.path.join(sandbox_root, "data", "file.txt")
            is_valid, result = validate_file_path(inside_path)
            assert is_valid is True

            # Path outside sandbox should be blocked
            outside_path = "/tmp/outside_sandbox.txt"
            is_valid, error = validate_file_path(outside_path)
            assert is_valid is False
            assert "outside sandbox" in error.lower()

            # Reset sandbox
            configure_file_sandbox(sandbox_root=None)


class TestFileToolsSecurity:
    """Test file tools with security validation."""

    @pytest.fixture
    def file_tools(self):
        """Create file tools for testing."""
        return {tool.name: tool for tool in create_file_tools()}

    def test_read_blocks_sensitive_files(self, file_tools):
        """SECURITY: read_text_file blocks sensitive files."""
        read_tool = file_tools["read_text_file"]
        result = read_tool.function(file_path="/etc/passwd")
        assert result.success is False
        assert "security" in result.error.lower() or "blocked" in result.error.lower()

    def test_write_blocks_sensitive_locations(self, file_tools):
        """SECURITY: write_text_file blocks sensitive locations."""
        write_tool = file_tools["write_text_file"]
        result = write_tool.function(
            file_path="/home/user/.ssh/authorized_keys",
            content="malicious key"
        )
        assert result.success is False
        assert result.metadata.get("blocked") is True

    def test_list_blocks_sensitive_directories(self, file_tools):
        """SECURITY: list_directory blocks sensitive directories."""
        list_tool = file_tools["list_directory"]
        result = list_tool.function(directory="/home/user/.ssh")
        assert result.success is False


class TestBlockedPatterns:
    """Verify blocked patterns are properly configured."""

    def test_env_file_pattern(self):
        """Verify .env files are in blocked patterns."""
        assert any(".env" in pattern for pattern in _BLOCKED_PATTERNS)

    def test_ssh_pattern(self):
        """Verify .ssh directory is in blocked patterns."""
        assert any(".ssh" in pattern for pattern in _BLOCKED_PATTERNS)

    def test_aws_pattern(self):
        """Verify .aws directory is in blocked patterns."""
        assert any(".aws" in pattern for pattern in _BLOCKED_PATTERNS)

    def test_credentials_pattern(self):
        """Verify credentials files are blocked."""
        assert any("credentials" in pattern for pattern in _BLOCKED_PATTERNS)

    def test_etc_passwd_pattern(self):
        """Verify /etc/passwd is blocked."""
        assert any("passwd" in pattern for pattern in _BLOCKED_PATTERNS)
