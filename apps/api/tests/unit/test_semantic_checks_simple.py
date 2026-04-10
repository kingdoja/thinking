"""
Simple unit tests for semantic consistency checks without database.

These tests verify the core logic of semantic checks using mock data.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, MagicMock

from app.services.qa_runtime import QARuntime, Issue


class TestCharacterConsistencySimple:
    """Test character consistency checking logic."""
    
    def test_character_consistency_with_undefined_character(self):
        """Test that undefined characters are detected."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock documents
        char_profile = Mock()
        char_profile.document_type = "character_profile"
        char_profile.content_jsonb = {
            "characters": [
                {"name": "Alice", "role": "Protagonist"}
            ]
        }
        
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "dialogues": [
                        {"character": "Bob", "text": "Hello"}  # Bob not defined
                    ]
                }
            ]
        }
        
        # Mock the repository to return our documents
        mock_doc_repo.list_for_episode.return_value = [char_profile, script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_character_consistency(episode_id)
        
        # Assert
        undefined_issues = [i for i in issues if i.type == "undefined_character"]
        assert len(undefined_issues) == 1
        assert "Bob" in undefined_issues[0].message
        assert undefined_issues[0].severity == "major"
    
    def test_character_consistency_with_unused_character(self):
        """Test that unused characters are detected."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock documents
        char_profile = Mock()
        char_profile.document_type = "character_profile"
        char_profile.content_jsonb = {
            "characters": [
                {"name": "Alice", "role": "Protagonist"},
                {"name": "Bob", "role": "Supporting"}  # Bob not used
            ]
        }
        
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "dialogues": [
                        {"character": "Alice", "text": "Hello"}
                    ]
                }
            ]
        }
        
        # Mock the repository to return our documents
        mock_doc_repo.list_for_episode.return_value = [char_profile, script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_character_consistency(episode_id)
        
        # Assert
        unused_issues = [i for i in issues if i.type == "unused_character"]
        assert len(unused_issues) == 1
        assert "Bob" in unused_issues[0].message
        assert unused_issues[0].severity == "info"


class TestWorldConsistencySimple:
    """Test world consistency checking logic."""
    
    def test_world_consistency_detects_anachronism(self):
        """Test that anachronisms are detected in medieval settings."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock documents
        story_bible = Mock()
        story_bible.document_type = "story_bible"
        story_bible.content_jsonb = {
            "setting": {
                "time_period": "medieval",
                "location_type": "fantasy kingdom"
            },
            "world_rules": []
        }
        
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "location": "Castle",
                    "action_text": "The knight pulls out his phone"
                }
            ]
        }
        
        # Mock the repository to return our documents
        mock_doc_repo.list_for_episode.return_value = [story_bible, script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_world_consistency(episode_id)
        
        # Assert
        violation_issues = [i for i in issues if i.type == "world_violation"]
        assert len(violation_issues) >= 1
        assert violation_issues[0].severity == "major"
    
    def test_world_consistency_detects_magic_violation(self):
        """Test that magic violations are detected."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock documents
        story_bible = Mock()
        story_bible.document_type = "story_bible"
        story_bible.content_jsonb = {
            "setting": {},
            "world_rules": [
                {"rule": "This world has no magic"}
            ]
        }
        
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "location": "Forest",
                    "action_text": "The wizard casts a spell"
                }
            ]
        }
        
        # Mock the repository to return our documents
        mock_doc_repo.list_for_episode.return_value = [story_bible, script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_world_consistency(episode_id)
        
        # Assert
        violation_issues = [i for i in issues if i.type == "world_violation"]
        assert len(violation_issues) >= 1
        assert violation_issues[0].severity == "major"


class TestPlotCoherenceSimple:
    """Test plot coherence checking logic."""
    
    def test_plot_coherence_detects_abrupt_transition(self):
        """Test that abrupt location changes are detected."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock document
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "location": "New York",
                    "action_text": "Walking in the city"
                },
                {
                    "scene_no": 2,
                    "location": "Tokyo",
                    "action_text": "Now in a different city"
                }
            ]
        }
        
        # Mock the repository to return our document
        mock_doc_repo.list_for_episode.return_value = [script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_plot_coherence(episode_id)
        
        # Assert
        transition_issues = [i for i in issues if i.type == "abrupt_transition"]
        assert len(transition_issues) >= 1
        assert transition_issues[0].severity == "minor"
    
    def test_plot_coherence_detects_timeline_inconsistency(self):
        """Test that timeline inconsistencies are detected."""
        # Arrange
        qa_runtime = QARuntime(None)
        episode_id = uuid4()
        
        # Mock the document repository
        mock_doc_repo = Mock()
        
        # Create mock document
        script = Mock()
        script.document_type = "script"
        script.content_jsonb = {
            "scenes": [
                {
                    "scene_no": 1,
                    "location": "Park",
                    "time_of_day": "evening",
                    "action_text": "The sun is setting"
                },
                {
                    "scene_no": 2,
                    "location": "Park",
                    "time_of_day": "morning",
                    "action_text": "Birds are chirping"
                }
            ]
        }
        
        # Mock the repository to return our document
        mock_doc_repo.list_for_episode.return_value = [script]
        
        # Patch the DocumentRepository
        from unittest.mock import patch
        with patch('app.repositories.document_repository.DocumentRepository', return_value=mock_doc_repo):
            # Act
            issues = qa_runtime.check_plot_coherence(episode_id)
        
        # Assert
        timeline_issues = [i for i in issues if i.type == "timeline_inconsistency"]
        assert len(timeline_issues) >= 1
        assert timeline_issues[0].severity == "minor"
