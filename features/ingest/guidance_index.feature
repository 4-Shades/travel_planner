@ingest
Feature: Guidance index management
  As an operator
  I want one command that builds and refreshes the guidance index from Wikivoyage
  So that the specialists have current, credited guidance to draw on

  Background:
    Given the MediaWiki API is a fake with articles for "Tokyo" and "Kyoto"
    And "data/rag/destinations.txt" lists "Tokyo" and "Kyoto"
    And today is "2026-10-24"

  @TP-SRS-100
  Scenario: The index is built from the destinations file
    When I run the ingest command
    Then the index holds passages for "Tokyo" and "Kyoto"

  @TP-SRS-101
  Scenario: Only the sections used by an agent are kept
    Given the Tokyo article has the sections "Understand", "History", "Get in", "See", and "Talk"
    When I run the ingest command
    Then the index holds Tokyo passages from "Understand", "Get in", and "See"
    And the index holds no passages from "History" or "Talk"

  @TP-SRS-101
  Scenario: Every passage is about 300 tokens and fully described
    When I run the ingest command
    Then every passage is about 300 tokens long
    And every passage records its destination, section, title, source URL, revision ID, license, language, and validity dates

  @TP-SRS-102
  Scenario: Passages expire one year after download
    When I run the ingest command
    Then every passage is valid from "2026-10-24" until "2027-10-24"

  @TP-SRS-103
  Scenario: Re-ingesting a destination replaces its passages
    Given I have run the ingest command
    And the Tokyo article has a new revision
    When I run the ingest command for "Tokyo" with a fresh download
    Then the number of Tokyo passages is the same as before
    And every Tokyo passage has the new revision ID

  @TP-SRS-104
  Scenario Outline: Downloaded articles are cached for 30 days
    Given I ran the ingest command <days> days ago
    When I run the ingest command
    Then the MediaWiki API is <called>

    Examples:
      | days | called     |
      | 29   | not called |
      | 31   | called     |

  @TP-SRS-104
  Scenario: Articles can be downloaded again on request
    Given I ran the ingest command 1 day ago
    When I run the ingest command with the refresh option
    Then the MediaWiki API is called for "Tokyo" and "Kyoto"

  @TP-SRS-105
  Scenario: A list of destinations can be ingested instead of the whole file
    When I run the ingest command for "Tokyo"
    Then the MediaWiki API is called only for "Tokyo"

  @TP-SRS-106 @TP-SRS-107
  Scenario Outline: A self-hosted or a cloud index can be built
    Given the embedding provider is "openai"
    When I run the ingest command with the <store> store
    Then a <store> index is built
    And the index records the embedding provider, model, and vector size

    Examples:
      | store  |
      | Chroma |
      | file   |

  @TP-SRS-106
  Scenario: A cloud index cannot be built with non-OpenAI embeddings
    Given the embedding provider is "ollama"
    When I run the ingest command with the file store
    Then the command fails with a message that the cloud index needs OpenAI embeddings
    And no index files are written

  @TP-SRS-171
  Scenario: The ingest command identifies itself to Wikimedia
    When I run the ingest command
    Then every MediaWiki request has a User-Agent header that includes a contact URL
