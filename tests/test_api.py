"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store initial state
    initial_activities = {
        "Basketball Team": {
            "description": "Join the varsity basketball team and compete against other schools",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu", "chris@mergington.edu"]
        },
        "Swimming Club": {
            "description": "Swim training and competitive meets",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 25,
            "participants": ["sarah@mergington.edu"]
        },
    }
    
    # Clear and reset activities
    activities.clear()
    activities.update(initial_activities)
    
    yield
    
    # Clean up after test
    activities.clear()
    activities.update(initial_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that get_activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Basketball Team" in data
        assert "Swimming Club" in data
        
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        basketball = data["Basketball Team"]
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
        assert isinstance(basketball["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up twice returns 400"""
        email = "duplicate@mergington.edu"
        
        # First signup
        response1 = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup (should fail)
        response2 = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response2.status_code == 400
        
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        # Add activity with special characters for testing
        activities["Art & Crafts"] = {
            "description": "Arts and crafts activities",
            "schedule": "Fridays, 3:00 PM - 4:00 PM",
            "max_participants": 10,
            "participants": []
        }
        
        response = client.post(
            "/activities/Art & Crafts/signup?email=artist@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # Verify participant exists
        activities_before = client.get("/activities").json()
        assert "alex@mergington.edu" in activities_before["Basketball Team"]["participants"]
        
        # Remove participant
        response = client.delete(
            "/activities/Basketball Team/participants/alex@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_after = client.get("/activities").json()
        assert "alex@mergington.edu" not in activities_after["Basketball Team"]["participants"]
    
    def test_remove_participant_activity_not_found(self, client):
        """Test removing participant from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_participant_not_found(self, client):
        """Test removing non-existent participant returns 404"""
        response = client.delete(
            "/activities/Basketball Team/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Student not found in this activity"
    
    def test_remove_participant_with_special_characters(self, client):
        """Test removing participant with special characters in email"""
        # Add participant with special characters
        special_email = "test+student@mergington.edu"
        activities["Basketball Team"]["participants"].append(special_email)
        
        response = client.delete(
            f"/activities/Basketball Team/participants/{special_email}"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for common user scenarios"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow of signing up and removing"""
        email = "workflow@mergington.edu"
        activity = "Swimming Club"
        
        # Get initial participants count
        initial = client.get("/activities").json()
        initial_count = len(initial[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        assert email in after_signup[activity]["participants"]
        
        # Remove
        remove_response = client.delete(f"/activities/{activity}/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify removed
        after_remove = client.get("/activities").json()
        assert len(after_remove[activity]["participants"]) == initial_count
        assert email not in after_remove[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test signing up for multiple different activities"""
        email = "multitask@mergington.edu"
        
        # Sign up for multiple activities
        response1 = client.post(f"/activities/Basketball Team/signup?email={email}")
        response2 = client.post(f"/activities/Swimming Club/signup?email={email}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify participant is in both
        all_activities = client.get("/activities").json()
        assert email in all_activities["Basketball Team"]["participants"]
        assert email in all_activities["Swimming Club"]["participants"]
