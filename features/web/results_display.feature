@web
Feature: Results display
  As a traveler
  I want to read the suggestions clearly, see what failed, and know where the advice came from
  So that I can judge the plan and its sources

  Background:
    Given I open the travel planner
    And I have filled in the form with a valid trip

  @TP-SRS-030
  Scenario: Flights, accommodation, and activities are shown in separate tables
    Given the planning service returns a plan with 3 flights, 2 stays, and 3 activities
    When I submit the form
    Then I see a "Flights" table with 3 rows
    And I see an "Accommodation" table with 2 rows
    And I see an "Activities" table with 3 rows

  @TP-SRS-031 @TP-SRS-180
  Scenario: Each failed part is named in a warning, and the other parts are still shown
    Given the planning service returns a plan with these errors:
      | part       | message                              |
      | flights    | Service is temporarily unavailable.  |
      | activities | Activity planner is temporarily unavailable. |
    And the plan has 2 stays
    When I submit the form
    Then I see a warning naming "flights" with "Service is temporarily unavailable."
    And I see a warning naming "activities" with "Activity planner is temporarily unavailable."
    And I see an "Accommodation" table with 2 rows

  @TP-SRS-032 @TP-SRS-170
  Scenario: Sources are listed in a collapsed section with links and licenses
    Given the planning service returns a plan with these sources:
      | title | url                                    | license      |
      | Tokyo | https://en.wikivoyage.org/wiki/Tokyo   | CC BY-SA 4.0 |
      | Kyoto | https://en.wikivoyage.org/wiki/Kyoto   | CC BY-SA 4.0 |
    When I submit the form
    Then I see a collapsed "Sources" section
    When I expand the "Sources" section
    Then I see a link "Tokyo" to "https://en.wikivoyage.org/wiki/Tokyo" with license "CC BY-SA 4.0"
    And I see a link "Kyoto" to "https://en.wikivoyage.org/wiki/Kyoto" with license "CC BY-SA 4.0"

  @TP-SRS-032
  Scenario: No Sources section is shown when the plan has no sources
    Given the planning service returns a plan with no sources
    When I submit the form
    Then I do not see a "Sources" section

  @TP-SRS-033
  Scenario: The page says suggestions are illustrative
    Then I see a notice that suggestions are illustrative and not live or bookable

  @TP-SRS-133
  Scenario: Results appear without a full page reload
    Given the planning service returns a plan with no errors
    When I submit the form
    Then I see the trip results
    And the page was not reloaded
