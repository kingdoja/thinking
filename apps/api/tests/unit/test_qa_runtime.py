"""
Unit tests for QA Runtime Service

Tests the QA Runtime's ability to:
1. Execute QA checks
2. Generate QA reports
3. Calculate QA results and scores
4. Decide workflow blocking
"""

import pytest
from uuid import uuid4

from app.services.qa_runtime import QARuntime, Issue, QAResult


class TestQARuntime:
    """Test QA Runtime functionality."""
    
    def test_calculate_qa_result_no_issues(self):
        """Test QA result calculation with no issues."""
        # Arrange
        issues = []
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)  # No DB needed for this test
        result = qa_runtime._calculate_qa_result(issues)
        
        # Assert
        assert result.result == "passed"
        assert result.score == 100.0
        assert result.severity == "info"
        assert result.issue_count == 0
        assert len(result.issues) == 0
    
    def test_calculate_qa_result_with_critical_issue(self):
        """Test QA result calculation with critical issue."""
        # Arrange
        issues = [
            Issue(
                type="missing_field",
                severity="critical",
                location="brief.genre",
                message="Genre field is required",
                suggestion="Add genre information",
            )
        ]
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        result = qa_runtime._calculate_qa_result(issues)
        
        # Assert
        assert result.result == "failed"
        assert result.score == 75.0  # 100 - 25 for critical
        assert result.severity == "critical"
        assert result.issue_count == 1
        assert len(result.issues) == 1
    
    def test_calculate_qa_result_with_multiple_issues(self):
        """Test QA result calculation with multiple issues of different severities."""
        # Arrange
        issues = [
            Issue(
                type="missing_field",
                severity="major",
                location="brief.genre",
                message="Genre field is missing",
            ),
            Issue(
                type="format_error",
                severity="minor",
                location="brief.title",
                message="Title format is incorrect",
            ),
            Issue(
                type="info",
                severity="info",
                location="brief.description",
                message="Description could be more detailed",
            ),
        ]
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        result = qa_runtime._calculate_qa_result(issues)
        
        # Assert
        assert result.result == "warning"  # Major issue triggers warning
        assert result.score == 86.0  # 100 - 10 (major) - 3 (minor) - 1 (info)
        assert result.severity == "major"
        assert result.issue_count == 3
    
    def test_should_block_workflow_with_critical_issue(self):
        """Test workflow blocking decision with critical issue."""
        # Arrange
        qa_result = QAResult(
            result="failed",
            score=50.0,
            severity="critical",
            issue_count=1,
            issues=[],
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        should_block = qa_runtime.should_block_workflow(qa_result)
        
        # Assert
        assert should_block is True
    
    def test_should_block_workflow_with_warning(self):
        """Test workflow blocking decision with warning."""
        # Arrange
        qa_result = QAResult(
            result="warning",
            score=85.0,
            severity="major",
            issue_count=1,
            issues=[],
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        should_block = qa_runtime.should_block_workflow(qa_result)
        
        # Assert
        assert should_block is False
    
    def test_should_block_workflow_passed(self):
        """Test workflow blocking decision with passed result."""
        # Arrange
        qa_result = QAResult(
            result="passed",
            score=100.0,
            severity="info",
            issue_count=0,
            issues=[],
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        should_block = qa_runtime.should_block_workflow(qa_result)
        
        # Assert
        assert should_block is False
    
    def test_score_calculation_with_many_issues(self):
        """Test that score doesn't go below 0."""
        # Arrange
        issues = [
            Issue(
                type="critical",
                severity="critical",
                location=f"field_{i}",
                message=f"Critical issue {i}",
            )
            for i in range(10)  # 10 critical issues = -250 points
        ]
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        result = qa_runtime._calculate_qa_result(issues)
        
        # Assert
        assert result.score == 0.0  # Should not go below 0
        assert result.result == "failed"
        assert result.severity == "critical"


class TestBriefRuleChecking:
    """Test Brief document rule checking."""
    
    def test_check_brief_rules_all_valid(self):
        """Test Brief rule checking with all valid fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="brief",
            content_jsonb={
                "title": "Test Story",
                "genre": "drama",
                "target_audience": "Young adults",
                "premise": "A compelling story about growth and discovery in a new world",
                "tone": "Inspirational and hopeful"
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_brief_rules(document)
        
        # Assert
        assert len(issues) == 0
    
    def test_check_brief_rules_missing_required_fields(self):
        """Test Brief rule checking with missing required fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="brief",
            content_jsonb={
                "title": "Test Story",
                # Missing: genre, target_audience, premise, tone
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_brief_rules(document)
        
        # Assert
        assert len(issues) == 4  # 4 missing required fields
        assert all(issue.severity == "major" for issue in issues)
        assert all(issue.type == "missing_field" for issue in issues)
    
    def test_check_brief_rules_title_too_long(self):
        """Test Brief rule checking with title exceeding max length."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="brief",
            content_jsonb={
                "title": "A" * 250,  # 250 characters, max is 200
                "genre": "drama",
                "target_audience": "Young adults",
                "premise": "A compelling story about growth",
                "tone": "Inspirational"
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_brief_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "minor"
        assert issues[0].type == "invalid_format"
        assert "title" in issues[0].location.lower()
    
    def test_check_brief_rules_premise_too_short(self):
        """Test Brief rule checking with premise too short."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="brief",
            content_jsonb={
                "title": "Test Story",
                "genre": "drama",
                "target_audience": "Young adults",
                "premise": "Short",  # Less than 20 characters
                "tone": "Inspirational"
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_brief_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "minor"
        assert "premise" in issues[0].location.lower()


class TestCharacterRuleChecking:
    """Test Character Profile document rule checking."""
    
    def test_check_character_rules_all_valid(self):
        """Test Character rule checking with all valid fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        "role": "Protagonist",
                        "personality": "Brave and curious",
                        "appearance": "Tall with long brown hair",
                        "visual_anchors": ["brown hair", "blue eyes", "red jacket"]
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_character_rules(document)
        
        # Assert
        assert len(issues) == 0
    
    def test_check_character_rules_no_characters(self):
        """Test Character rule checking with no characters."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="character_profile",
            content_jsonb={
                "characters": []
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_character_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "critical"
        assert issues[0].type == "missing_field"
    
    def test_check_character_rules_missing_required_fields(self):
        """Test Character rule checking with missing required fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        # Missing: role, personality, appearance
                        "visual_anchors": ["brown hair"]
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_character_rules(document)
        
        # Assert
        # 3 missing required fields + 1 info about visual anchors being < 3
        assert len(issues) == 4
        major_issues = [i for i in issues if i.severity == "major"]
        assert len(major_issues) == 3
    
    def test_check_character_rules_no_visual_anchors(self):
        """Test Character rule checking with no visual anchors."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        "role": "Protagonist",
                        "personality": "Brave",
                        "appearance": "Tall",
                        "visual_anchors": []
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_character_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "minor"
        assert "visual_anchors" in issues[0].location


class TestScriptRuleChecking:
    """Test Script document rule checking."""
    
    def test_check_script_rules_all_valid(self):
        """Test Script rule checking with all valid fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "duration_sec": 60,
                        "dialogues": [
                            {
                                "character": "Alice",
                                "text": "Hello, world!"
                            }
                        ]
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_script_rules(document)
        
        # Assert
        assert len(issues) == 0
    
    def test_check_script_rules_no_scenes(self):
        """Test Script rule checking with no scenes."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="script",
            content_jsonb={
                "scenes": []
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_script_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "critical"
    
    def test_check_script_rules_missing_scene_fields(self):
        """Test Script rule checking with missing scene fields."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        # Missing: scene_no, location
                        "duration_sec": 60,
                        "dialogues": []
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_script_rules(document)
        
        # Assert
        # Should have issues for missing scene_no, location, and no dialogues
        assert len(issues) >= 2
        major_issues = [i for i in issues if i.severity == "major"]
        assert len(major_issues) >= 2
    
    def test_check_script_rules_invalid_duration(self):
        """Test Script rule checking with invalid duration."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "duration_sec": 0,  # Invalid
                        "dialogues": [{"character": "Alice", "text": "Hi"}]
                    }
                ]
            }
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_script_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "major"
        assert "duration" in issues[0].location.lower()


class TestStoryboardRuleChecking:
    """Test Storyboard document rule checking."""
    
    def test_check_storyboard_rules_no_episode_id(self):
        """Test Storyboard rule checking with no episode_id."""
        # Arrange
        from app.db.models import DocumentModel
        document = DocumentModel(
            document_type="storyboard",
            episode_id=None,
            content_jsonb={}
        )
        
        # Act
        from app.services.qa_runtime import QARuntime
        qa_runtime = QARuntime(None)
        issues = qa_runtime.check_storyboard_rules(document)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "critical"
        assert "episode_id" in issues[0].location



class TestSemanticConsistencyChecks:
    """Test semantic consistency checking functionality."""
    
    def test_check_character_consistency_no_character_profile(self, test_session):
        """Test character consistency check when Character Profile is missing."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Only create Script, no Character Profile
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "dialogues": [
                            {"character": "Alice", "text": "Hello"}
                        ]
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_character_consistency(episode.id)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert "Character Profile" in issues[0].message
    
    def test_check_character_consistency_undefined_character(self, test_session):
        """Test character consistency check with undefined character in script."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Character Profile with Alice
        char_profile = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        "role": "Protagonist",
                        "personality": "Brave",
                        "appearance": "Tall"
                    }
                ]
            }
        )
        test_session.add(char_profile)
        
        # Create Script using Bob (not defined in Character Profile)
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "dialogues": [
                            {"character": "Bob", "text": "Hello"}
                        ]
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_character_consistency(episode.id)
        
        # Assert
        assert len(issues) >= 1
        undefined_issues = [i for i in issues if i.type == "undefined_character"]
        assert len(undefined_issues) == 1
        assert "Bob" in undefined_issues[0].message
        assert undefined_issues[0].severity == "major"
    
    def test_check_character_consistency_unused_character(self, test_session):
        """Test character consistency check with unused character."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Character Profile with Alice and Bob
        char_profile = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        "role": "Protagonist",
                        "personality": "Brave",
                        "appearance": "Tall"
                    },
                    {
                        "name": "Bob",
                        "role": "Supporting",
                        "personality": "Funny",
                        "appearance": "Short"
                    }
                ]
            }
        )
        test_session.add(char_profile)
        
        # Create Script using only Alice
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "dialogues": [
                            {"character": "Alice", "text": "Hello"}
                        ]
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_character_consistency(episode.id)
        
        # Assert
        unused_issues = [i for i in issues if i.type == "unused_character"]
        assert len(unused_issues) == 1
        assert "Bob" in unused_issues[0].message
        assert unused_issues[0].severity == "info"
    
    def test_check_character_consistency_all_consistent(self, test_session):
        """Test character consistency check with all characters consistent."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Character Profile
        char_profile = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="character_profile",
            content_jsonb={
                "characters": [
                    {
                        "name": "Alice",
                        "role": "Protagonist",
                        "personality": "Brave",
                        "appearance": "Tall"
                    }
                ]
            }
        )
        test_session.add(char_profile)
        
        # Create Script using Alice
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "dialogues": [
                            {"character": "Alice", "text": "Hello"}
                        ]
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_character_consistency(episode.id)
        
        # Assert
        assert len(issues) == 0
    
    def test_check_world_consistency_no_story_bible(self, test_session):
        """Test world consistency check when Story Bible is missing."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Only create Script, no Story Bible
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Castle",
                        "action_text": "The knight draws his sword"
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_world_consistency(episode.id)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert "Story Bible" in issues[0].message
    
    def test_check_world_consistency_anachronism_detected(self, test_session):
        """Test world consistency check detecting anachronisms."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Story Bible with medieval setting
        story_bible = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="story_bible",
            content_jsonb={
                "setting": {
                    "time_period": "medieval",
                    "location_type": "fantasy kingdom"
                },
                "world_rules": []
            }
        )
        test_session.add(story_bible)
        
        # Create Script with modern elements
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Castle",
                        "action_text": "The knight pulls out his phone to call for help"
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_world_consistency(episode.id)
        
        # Assert
        world_violation_issues = [i for i in issues if i.type == "world_violation"]
        assert len(world_violation_issues) >= 1
        assert "phone" in world_violation_issues[0].message.lower()
        assert world_violation_issues[0].severity == "major"
    
    def test_check_world_consistency_magic_rule_violation(self, test_session):
        """Test world consistency check detecting magic rule violations."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Story Bible with no magic rule
        story_bible = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="story_bible",
            content_jsonb={
                "setting": {},
                "world_rules": [
                    {"rule": "This world has no magic"}
                ]
            }
        )
        test_session.add(story_bible)
        
        # Create Script with magic
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Forest",
                        "action_text": "The wizard casts a powerful spell"
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_world_consistency(episode.id)
        
        # Assert
        world_violation_issues = [i for i in issues if i.type == "world_violation"]
        assert len(world_violation_issues) >= 1
        assert world_violation_issues[0].severity == "major"
    
    def test_check_plot_coherence_no_script(self, test_session):
        """Test plot coherence check when Script is missing."""
        # Arrange
        from app.db.models import EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_plot_coherence(episode.id)
        
        # Assert
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert "Script" in issues[0].message
    
    def test_check_plot_coherence_abrupt_location_change(self, test_session):
        """Test plot coherence check detecting abrupt location changes."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Script with abrupt location change
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "New York",
                        "action_text": "Alice is walking in the city"
                    },
                    {
                        "scene_no": 2,
                        "location": "Tokyo",
                        "action_text": "Alice is now in a different city"
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_plot_coherence(episode.id)
        
        # Assert
        transition_issues = [i for i in issues if i.type == "abrupt_transition"]
        assert len(transition_issues) >= 1
        assert transition_issues[0].severity == "minor"
    
    def test_check_plot_coherence_timeline_inconsistency(self, test_session):
        """Test plot coherence check detecting timeline inconsistencies."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Script with time going backwards
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
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
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_plot_coherence(episode.id)
        
        # Assert
        timeline_issues = [i for i in issues if i.type == "timeline_inconsistency"]
        assert len(timeline_issues) >= 1
        assert timeline_issues[0].severity == "minor"
    
    def test_check_plot_coherence_character_continuity(self, test_session):
        """Test plot coherence check detecting character continuity issues."""
        # Arrange
        from app.db.models import DocumentModel, EpisodeModel, ProjectModel
        from app.services.qa_runtime import QARuntime
        
        project = ProjectModel(name="Test Project", source_mode="ai", target_platform="web")
        test_session.add(project)
        test_session.flush()
        
        episode = EpisodeModel(project_id=project.id, episode_no=1, target_duration_sec=300)
        test_session.add(episode)
        test_session.flush()
        
        # Create Script with character appearing, disappearing, and reappearing
        script = DocumentModel(
            project_id=project.id,
            episode_id=episode.id,
            document_type="script",
            content_jsonb={
                "scenes": [
                    {
                        "scene_no": 1,
                        "location": "Park",
                        "dialogues": [{"character": "Alice", "text": "Hello"}]
                    },
                    {
                        "scene_no": 2,
                        "location": "Street",
                        "dialogues": [{"character": "Bob", "text": "Hi"}]
                    },
                    {
                        "scene_no": 3,
                        "location": "Cafe",
                        "dialogues": [{"character": "Bob", "text": "Coffee?"}]
                    },
                    {
                        "scene_no": 4,
                        "location": "Office",
                        "dialogues": [{"character": "Bob", "text": "Work"}]
                    },
                    {
                        "scene_no": 5,
                        "location": "Park",
                        "dialogues": [{"character": "Alice", "text": "I'm back"}]
                    }
                ]
            }
        )
        test_session.add(script)
        test_session.commit()
        
        # Act
        qa_runtime = QARuntime(test_session)
        issues = qa_runtime.check_plot_coherence(episode.id)
        
        # Assert
        continuity_issues = [i for i in issues if i.type == "character_continuity"]
        assert len(continuity_issues) >= 1
        assert continuity_issues[0].severity == "info"
