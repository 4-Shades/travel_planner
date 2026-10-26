@web
Feature: Usability
  As a traveler on any device
  I want the planner to work with a keyboard and on small screens
  So that I can use it however I browse

  @TP-SRS-130
  Scenario: Every form field is labelled and keyboard operable
    When I open the travel planner
    Then an accessibility check finds no form fields without a label
    And I can reach every form field and the submit button with the Tab key

  @TP-SRS-131
  Scenario Outline: The page fits the screen without horizontal scrolling
    Given my screen is <width> pixels wide
    When I open the travel planner and plan a valid trip
    Then the page has no horizontal scrolling before or after the results appear

    Examples:
      | width |
      | 360   |
      | 768   |
      | 1280  |
