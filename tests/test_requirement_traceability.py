import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_PATTERN = re.compile(r"\*\*([A-Z]+-\d{3})")

# This is the complete durable-requirement audit trail. A selector identifies an
# existing behavioral test as path::Class.method. Keep focused requirement IDs
# in individual test docstrings when they are useful at the test site.
REQUIREMENT_TESTS = {
    "META-001": ("tests/test_metadata_manager.py::MetadataManagerTests.test_reconcile_metadata_creates_creator_and_project_files",),
    "META-002": ("tests/test_library_metadata.py::LibraryMetadataTests.test_metadata_file_schema_rejects_folder_derived_name_and_title",),
    "META-003": ("tests/test_library_builder.py::LibraryBuilderTests.test_creator_metadata_file_builds_typed_library",),
    "META-004": ("tests/test_library_builder.py::LibraryBuilderTests.test_collaboration_links_are_computed_in_memory",),
    "META-005": ("tests/test_metadata_manager.py::MetadataManagerTests.test_reconcile_metadata_creates_creator_and_project_files",),
    "META-006": ("tests/test_library_builder.py::LibraryBuilderTests.test_creator_metadata_file_builds_typed_library",),
    "META-007": ("tests/test_metadata_manager.py::MetadataManagerTests.test_reconcile_metadata_prunes_inactive_type_branch_with_values",),
    "META-008": ("tests/test_metadata_manager.py::MetadataManagerTests.test_reconcile_metadata_prunes_empty_stale_facets_but_keeps_values",),
    "META-009": ("tests/test_library_metadata.py::LibraryMetadataTests.test_date_display_preserves_stored_precision",),
    "META-010": ("tests/test_metadata_templates.py::MetadataTemplateTests.test_metadata_schemas_reject_portrait_and_cover_paths",),
    "LIFE-001": ("tests/test_html_build.py::HtmlBuildTests.test_cli_accepts_revised_destructive_names_and_rejects_removed_names",),
    "LIFE-002": ("tests/test_html_build.py::HtmlBuildTests.test_build_command_uses_configured_project_facets_without_domain_arg",),
    "LIFE-003": ("tests/test_html_build.py::HtmlBuildTests.test_build_command_uses_configured_project_facets_without_domain_arg",),
    "LIFE-004": ("tests/test_html_build.py::HtmlBuildTests.test_build_domain_override_replaces_configured_project_facets",),
    "LIFE-005": ("tests/test_config_manager.py::ConfigManagerTests.test_portrait_overrides_do_not_reset_when_omitted",),
    "LIFE-006": ("tests/test_config_manager.py::ConfigManagerTests.test_gallery_aspect_ratio_config_normalizes_supported_values",),
    "BUILD-001": ("tests/test_library_builder.py::LibraryBuilderTests.test_invalid_project_metadata_skips_project_not_creator_in_best_effort_mode",),
    "BUILD-002": ("tests/test_library_builder.py::LibraryBuilderTests.test_invalid_metadata_raises_in_strict_mode",),
    "BUILD-003": ("tests/test_library_issues.py::LibraryIssuesTests.test_issue_from_metadata_exception_preserves_code",),
    "BUILD-004": ("tests/test_html_build.py::HtmlBuildTests.test_build_command_combines_render_asset_issues_into_final_summary",),
    "BUILD-005": ("tests/test_library_issues.py::LibraryIssuesTests.test_non_strict_policy_deduplicates_scope_code_and_path",),
    "BUILD-006": ("tests/test_build_summary.py::BuildSummaryTests.test_summary_reports_timings_and_asset_statistics",),
    "BUILD-007": ("tests/test_build_summary.py::BuildSummaryTests.test_summary_reports_timings_and_asset_statistics",),
    "BUILD-008": ("tests/test_html_build.py::HtmlBuildTests.test_main_uses_usage_exit_for_invalid_paths",),
    "BUILD-009": ("tests/test_build_runner.py::BuildRunnerTests.test_runner_combines_and_deduplicates_phase_issues",),
    "CLI-001": ("tests/test_html_build.py::HtmlBuildTests.test_cli_help_describes_commands_and_destructive_options_precisely",),
    "CLI-002": ("tests/test_html_build.py::HtmlBuildTests.test_cli_accepts_revised_destructive_names_and_rejects_removed_names",),
    "CLI-003": ("tests/test_html_build.py::HtmlBuildTests.test_main_uses_usage_exit_for_invalid_paths",),
    "ASSET-001": ("tests/test_render_media.py::RenderMediaTests.test_missing_media_is_omitted_and_reported",),
    "ASSET-002": ("tests/test_media_staging.py::MediaStagingTests.test_thumbnail_failure_uses_default_and_reports_issue",),
    "ASSET-003": ("tests/test_render_media.py::RenderMediaTests.test_unreadable_gallery_image_is_omitted_and_reported",),
    "ASSET-004": ("tests/test_render_media.py::RenderMediaTests.test_audio_inspection_failure_uses_zero_and_reports_warning",),
    "ASSET-005": ("tests/test_media_staging.py::MediaStagingTests.test_thumbnail_failure_raises_in_strict_mode",),
    "ASSET-006": ("tests/test_media_staging.py::MediaStagingTests.test_stage_media_file_uses_hardlink_when_symlink_is_unavailable",),
    "ASSET-007": ("tests/test_media_staging.py::MediaStagingTests.test_stage_media_file_aborts_when_links_are_unavailable",),
    "ASSET-008": ("tests/test_library_scan.py::LibraryScanTests.test_nested_portrait_and_cover_names_are_selected_lexicographically",),
    "ASSET-009": ("tests/test_library_scan.py::LibraryScanTests.test_auto_portrait_discovery_selects_portrait_orientation_but_not_landscape_fallback",),
    "ASSET-010": ("tests/test_library_scan.py::LibraryScanTests.test_cover_falls_back_to_landscape_then_any_image",),
    "ASSET-011": ("tests/test_library_scan.py::LibraryScanTests.test_video_posters_use_common_order_and_all_candidates_are_excluded",),
    "ASSET-012": ("tests/test_library_scan.py::LibraryScanTests.test_all_named_role_candidates_are_excluded_from_galleries",),
    "THUMB-001": ("tests/test_media_staging.py::MediaStagingTests.test_thumbnail_is_regenerated_when_content_changes_with_preserved_timestamps",),
    "THUMB-002": ("tests/test_media_staging.py::MediaStagingTests.test_generated_thumbnail_stores_authoritative_source_hash",),
    "THUMB-003": ("tests/test_media_staging.py::MediaStagingTests.test_existing_thumbnail_is_reused_only_when_source_hash_matches",),
    "THUMB-004": ("tests/test_media_staging.py::MediaStagingTests.test_thumbnail_is_regenerated_when_content_changes_with_preserved_timestamps",),
    "SITE-001": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_starting_media_pauses_only_the_previously_active_player",),
    "SITE-002": ("tests/test_js_contracts.py::JavaScriptContractTests.test_playback_coordinator_uses_captured_native_media_events_and_only_pauses",),
    "SITE-003": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_restricted_local_storage_does_not_hide_or_break_page",),
    "SITE-004": ("tests/test_template_renderer.py::TemplateRendererTests.test_video_source_does_not_claim_an_incorrect_media_type",),
    "SITE-005": ("tests/test_template_renderer.py::TemplateRendererTests.test_gallery_image_alt_text_uses_available_image_metadata",),
    "SITE-006": ("tests/test_template_renderer.py::TemplateRendererTests.test_media_controls_render_native_semantics_and_accessible_names",),
    "SITE-007": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_focus_indicator_is_keyboard_only",),
    "SITE-008": ("tests/test_js_contracts.py::JavaScriptContractTests.test_toggle_scripts_expose_pressed_state",),
    "SITE-009": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_theme_dropdown_supports_keyboard_navigation_and_escape",),
    "SITE-010": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_audio_track_list_supports_roving_keyboard_navigation",),
    "SITE-011": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_logo_remains_active_and_consistent_across_pages_and_themes",),
    "SITE-012": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_detail_content_is_visible_and_ordered_on_mobile_without_javascript",),
    "SITE-013": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_gallery_lightbox_uses_native_navigation_and_traps_focus",),
    "SITE-014": ("tests/test_overview_contexts.py::OverviewContextTests.test_disabled_portraits_build_text_summary_without_thumbnail_work",),
    "SITE-015": ("tests/test_page_contexts.py::PageContextTests.test_details_portraits_render_discovered_portrait_without_missing_default",),
    "SITE-016": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_detail_metadata_uses_stacked_semantic_presentation_and_preserves_image_layouts",),
    "SITE-017": ("tests/test_render_metadata.py::RenderMetadataTests.test_creator_event_entries_combine_visible_date_and_place",),
    "SITE-018": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_tags_page_renders_and_initializes_theme",),
    "SITE-019": ("tests/test_library_scan.py::LibraryScanTests.test_media_groups_prioritize_root_then_configured_metadata_folder",),
    "SITE-020": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_reduced_motion_disables_shared_transitions_and_smooth_pagination_scroll",),
    "SITE-021": ("tests/test_config_manager.py::ConfigManagerTests.test_complete_phrase_formats_are_configurable_and_reorder_named_values",),
    "SITE-022": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_saved_theme_is_applied_before_theme_menu_initializes",),
    "SITE-023": ("tests/test_template_renderer.py::TemplateRendererTests.test_empty_overview_templates_render_static_empty_state_without_search_or_cards",),
    "SITE-024": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_detail_breadcrumb_wraps_without_moving_primary_header_controls",),
    "SITE-025": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_navigation_and_page_content_use_distinct_aligned_geometry",),
    "SITE-026": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_content_first_typography_hierarchy",),
    "SITE-027": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_page_section_and_gallery_spacing_follow_layout_tokens",),
    "SITE-028": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_details_portrait_visibility_uses_text_overview_and_detail_portraits",),
    "SITE-029": ("tests/test_overview_contexts.py::OverviewContextTests.test_disabled_portraits_build_text_summary_without_thumbnail_work",),
    "SITE-030": ("tests/test_render_media.py::RenderMediaTests.test_sort_media_sections_accepts_enum_and_string_order",),
    "SITE-031": ("tests/test_config_manager.py::ConfigManagerTests.test_project_count_labels_are_configurable_independently_from_entity_labels",),
    "SITE-032": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_no_javascript_overview_gallery_fallback_remains_visible",),
    "SITE-033": ("tests/test_template_renderer.py::TemplateRendererTests.test_detail_templates_render_region_empty_states_only_when_whole_region_is_empty",),
    "SITE-034": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_tags_page_renders_and_initializes_theme",),
    "THEME-001": ("tests/test_html_build.py::HtmlBuildTests.test_streaming_html_build_copies_and_renders_custom_theme",),
    "THEME-002": ("tests/test_themes.py::ThemeTests.test_custom_theme_is_discovered_from_explicit_directory",),
    "THEME-003": ("tests/test_themes.py::ThemeTests.test_invalid_custom_themes_are_reported_and_skipped",),
    "THEME-004": ("tests/test_themes.py::ThemeTests.test_duplicate_custom_theme_is_reported_and_builtin_wins",),
    "THEME-005": ("tests/test_html_build.py::HtmlBuildTests.test_build_command_aborts_before_side_effects_for_missing_themes_directory",),
    "THEME-006": ("tests/test_themes.py::ThemeTests.test_builtin_registry_uses_self_contained_theme_files_and_explicit_default",),
    "THEME-007": ("tests_browser/test_rendered_site.py::RenderedSiteBrowserTests.test_restricted_local_storage_does_not_hide_or_break_page",),
    "THEME-008": ("tests/test_js_contracts.py::JavaScriptContractTests.test_public_theme_tokens_cover_navigation_pagination_and_track_separators",),
    "ARCH-001": ("tests/test_html_build.py::HtmlBuildTests.test_streaming_html_build_renders_from_lightweight_index",),
    "ARCH-002": ("tests/test_library_builder.py::LibraryBuilderTests.test_library_index_keeps_lightweight_creator_and_project_summaries",),
    "ARCH-003": ("tests/test_media_cache.py::MediaInfoCacheTests.test_image_dimensions_are_reused_and_bounded",),
}


def _requirement_ids() -> set[str]:
    return set(REQUIREMENT_PATTERN.findall((ROOT / "info" / "REQUIREMENTS.md").read_text(encoding="utf-8")))


def _test_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                symbols.add(f"{node.name}.{child.name}")
    return symbols


class RequirementTraceabilityTests(unittest.TestCase):
    def test_every_durable_requirement_maps_to_an_existing_behavioral_test(self):
        requirement_ids = _requirement_ids()

        self.assertEqual(set(REQUIREMENT_TESTS), requirement_ids)

        symbols_by_path = {}
        for requirement_id, selectors in REQUIREMENT_TESTS.items():
            self.assertTrue(selectors, requirement_id)
            for selector in selectors:
                relative_path, symbol = selector.split("::", 1)
                path = ROOT / relative_path
                self.assertTrue(path.is_file(), selector)
                symbols = symbols_by_path.setdefault(path, _test_symbols(path))
                self.assertIn(symbol, symbols, selector)


if __name__ == "__main__":
    unittest.main()
