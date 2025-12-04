#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build combined decision tree from Lead and NoLead ranges

Process:
1. Load both Lead and NoLead ranges
2. Add 'nolead' binary feature (0 for Lead, 1 for NoLead)
3. Combine all data with 86 features (85 buckets + nolead)
4. Build decision tree
5. Export to Mermaid format
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
from sklearn.tree import DecisionTreeClassifier
import json
import sys

# Add path to lib for direct module import
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

import card
import buckets

Card = card.Card
get_all_buckets = buckets.get_all_buckets

# Bucket names mapping (85 features in order)
BUCKET_NAMES = [
    'flush_royal', 'flush', 'nut_flush', 'nut_flush2', 'not_nut_flush',
    'flush_draw', 'not_nut_flush_draw', 'nut_flush_draw', 'nut_flush_draw2',
    'set', 'top_set', 'middle_set', 'bottom_set', 'two_sets',
    'trips', 'quads', 'full_house', 'full_house_nut', 'full_house_not_nut',
    'pocket_pair', 'pair', 'top_pair', 'middle_pair', 'bottom_pair',
    'tp_tk', 'two_pairs', 'top_two_pairs', 'top_and_bottom_pairs', 'bottom_two_pairs',
    'three_pairs', 'over_pair', 'two_over_pairs',
    'straight_flush', 'straight_nut', 'straight_nut2', 'straight_nut3', 'straight',
    'straight_draw', 'no_draw', 'backdoor_straight_draw', 'backdoor_straight_draw4',
    'bdfd', 'bdfd1', 'bdfd2', 'bdfd_nut',
    'gutshot', 'oesd', 'wrap', 'wrap9', 'wrap12', 'wrap13',
    'minor_wrap', 'wrap16', 'wrap17', 'wrap20', 'major_wrap',
    'flush_blocker', 'flush_blocker_nut', 'flush_blocker_nut2',
    'flush_draw_blocker', 'flush_draw_blocker_nut', 'flush_draw_blocker1',
    'flush_draw_blocker2', 'flush_draw_blocker_nut2',
    'straight_blocker', 'straight_blocker1', 'straight_blocker2',
    'straight_blocker3', 'straight_blocker4',
    'straight_blocker_nut', 'straight_blocker_nut1', 'straight_blocker_nut2',
    'straight_blocker_nut3', 'straight_blocker_nut4',
    'straight_draw_blocker', 'straight_draw_blocker1', 'straight_draw_blocker2',
    'straight_draw_blocker3', 'straight_draw_blocker4',
    'straight_draw_blocker_nut', 'straight_draw_blocker_nut1',
    'straight_draw_blocker_nut2', 'straight_draw_blocker_nut3',
    'straight_draw_blocker_nut4'
]


def load_range_csv(csv_path: str, board: str, nolead_flag: int) -> pd.DataFrame:
    """
    Load CSV with range and add buckets + nolead flag

    Args:
        csv_path: Path to CSV file (combo, weight, ev)
        board: Board string (e.g. "9s6d5c")
        nolead_flag: 0 for Lead, 1 for NoLead

    Returns:
        DataFrame with columns: combo, weight, ev, nolead, bucket features...
    """
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} combos from {csv_path}")

    bucket_data = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Bucketing"):
        combo_str = row['combo']

        try:
            # Get buckets (85 elements)
            buckets_result = get_all_buckets(combo_str, board)

            # Form row with data
            bucket_row = {
                'combo': combo_str,
                'weight': row['weight'],
                'ev': row['ev'],
                'nolead': nolead_flag  # Add NoLead flag
            }

            # Add buckets with readable names
            for i, bucket_value in enumerate(buckets_result):
                bucket_row[BUCKET_NAMES[i]] = int(bucket_value)

            bucket_data.append(bucket_row)

        except Exception as e:
            print(f"Error processing {combo_str}: {e}")
            continue

    df_buckets = pd.DataFrame(bucket_data)

    print(f"Processed {len(df_buckets)} combos with buckets + nolead flag")

    return df_buckets


def combine_all_ranges(range_files_lead: Dict[str, str],
                       range_files_nolead: Dict[str, str],
                       board: str) -> pd.DataFrame:
    """
    Combine Lead and NoLead ranges with nolead flag

    Args:
        range_files_lead: Dict {action_name: csv_path} for Lead
        range_files_nolead: Dict {action_name: csv_path} for NoLead
        board: Board string (e.g. "9s6d5c")

    Returns:
        DataFrame with columns: combo, action, weight, ev, nolead, bucket features...
    """
    all_data = []

    # Load Lead ranges (nolead=0)
    print("\n" + "=" * 60)
    print("Loading LEAD ranges (nolead=0)")
    print("=" * 60)

    for action_name, csv_path in range_files_lead.items():
        print(f"\nLoading Lead {action_name} from {csv_path}")

        df = load_range_csv(csv_path, board, nolead_flag=0)
        df['action'] = action_name

        all_data.append(df)

    # Load NoLead ranges (nolead=1)
    print("\n" + "=" * 60)
    print("Loading NOLEAD ranges (nolead=1)")
    print("=" * 60)

    for action_name, csv_path in range_files_nolead.items():
        print(f"\nLoading NoLead {action_name} from {csv_path}")

        df = load_range_csv(csv_path, board, nolead_flag=1)
        df['action'] = action_name

        all_data.append(df)

    # Combine all
    df_combined = pd.concat(all_data, ignore_index=True)

    print(f"\n" + "=" * 60)
    print("COMBINED DATA")
    print("=" * 60)
    print(f"Total rows: {len(df_combined)}")
    print(f"Actions: {df_combined['action'].value_counts().to_dict()}")
    print(f"NoLead distribution:")
    print(df_combined['nolead'].value_counts())

    return df_combined


def build_combined_matrix(df_combined: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Build bucket matrix with nolead feature

    Args:
        df_combined: DataFrame with combo, action, weight, ev, nolead, buckets

    Returns:
        (Matrix: bucket features + nolead x actions, action list)
    """
    # Feature columns = 85 buckets + nolead
    feature_columns = ['nolead'] + BUCKET_NAMES

    print(f"\nFeature columns: {len(feature_columns)} (1 nolead + 85 buckets)")

    # Group by features and actions
    df_grouped = df_combined.groupby(feature_columns + ['action'], as_index=False).agg({
        'weight': 'sum',
        'ev': 'mean'
    })

    print(f"Unique feature combinations after grouping: {len(df_grouped[feature_columns].drop_duplicates())}")

    # Pivot to create matrix
    df_pivot = df_grouped.pivot_table(
        index=feature_columns,
        columns='action',
        values='weight',
        fill_value=0
    ).reset_index()

    # Get list of actions
    actions = df_combined['action'].unique().tolist()

    # Ensure all action columns exist
    for action in actions:
        if action not in df_pivot.columns:
            df_pivot[action] = 0

    # Calculate total weight for each bucket
    df_pivot['total_weight'] = df_pivot[actions].sum(axis=1)

    # Normalize to percentages
    for action in actions:
        df_pivot[action] = (df_pivot[action] / df_pivot['total_weight'] * 100).fillna(0)

    # Round
    for action in actions:
        df_pivot[action] = df_pivot[action].round(2)

    df_pivot['total_weight'] = df_pivot['total_weight'].round(2)

    # Reorder columns
    final_columns = actions + ['total_weight'] + feature_columns
    df_pivot = df_pivot[final_columns]

    df_pivot = df_pivot.sort_values(feature_columns).reset_index(drop=True)

    print(f"\nCombined matrix created!")
    print(f"Feature combinations: {len(df_pivot)}")
    print(f"Columns: {len(df_pivot.columns)}")

    return df_pivot, actions


def tree_to_mermaid(tree, feature_names: List[str], class_names: List[str],
                    node: int = 0, node_id_prefix: str = 'node',
                    include_styles: bool = False) -> List[str]:
    """
    Convert sklearn tree to Mermaid flowchart format

    Args:
        tree: sklearn tree object (clf.tree_)
        feature_names: List of feature names (including 'nolead')
        class_names: List of class names (actions)
        node: Current node (for recursion)
        node_id_prefix: Prefix for node IDs
        include_styles: Add styles (colors)

    Returns:
        List of Mermaid diagram lines
    """
    lines = []
    node_id = f"{node_id_prefix}{node}"

    if tree.feature[node] == -2:  # Leaf node
        values = tree.value[node][0]
        total = sum(values)
        class_idx = values.argmax()
        class_name = class_names[class_idx]

        label = class_name

        # Add percentages
        percentages = []
        for i, value in enumerate(values):
            if value > 0:
                pct = (value / total) * 100
                percentages.append(f"{class_names[i]}: {pct:.1f}%")

        if len(percentages) > 1:
            label += "<br/>" + "<br/>".join(percentages)

        lines.append(f'    {node_id}["{label}"]')

        if include_styles:
            lines.append(f'    style {node_id} fill:#90EE90')

        return lines

    # Split node
    feature = feature_names[tree.feature[node]]
    threshold = tree.threshold[node]

    # Use readable feature name
    label = feature

    lines.append(f'    {node_id}{{"{label}"}}')

    # Process left subtree
    left_child = tree.children_left[node]
    left_node_id = f"{node_id_prefix}{left_child}"
    left_lines = tree_to_mermaid(tree, feature_names, class_names, left_child, node_id_prefix, include_styles)

    # For binary features: left = 0 (No), right = 1 (Yes)
    lines.append(f'    {node_id} -->|No| {left_node_id}')

    lines.extend(left_lines)

    # Process right subtree
    right_child = tree.children_right[node]
    right_node_id = f"{node_id_prefix}{right_child}"
    right_lines = tree_to_mermaid(tree, feature_names, class_names, right_child, node_id_prefix, include_styles)

    lines.append(f'    {node_id} -->|Yes| {right_node_id}')

    lines.extend(right_lines)

    return lines


def build_decision_tree(df_matrix: pd.DataFrame, actions: List[str],
                       min_leaf: int = 1) -> Tuple[DecisionTreeClassifier, List[str]]:
    """
    Build decision tree with nolead feature

    Args:
        df_matrix: Bucket matrix with nolead
        actions: List of actions
        min_leaf: Minimum samples in leaf

    Returns:
        (trained classifier, feature_columns)
    """
    # Define target variable
    df_matrix['target'] = df_matrix[actions].idxmax(axis=1)

    print(f"\nTarget action distribution:")
    print(df_matrix['target'].value_counts())

    # Features = nolead + 85 buckets
    feature_columns = ['nolead'] + BUCKET_NAMES

    print(f"\nFeatures: {len(feature_columns)} (nolead + 85 buckets)")

    X = df_matrix[feature_columns]
    y = df_matrix['target']
    weights = df_matrix['total_weight']

    # Train tree
    clf = DecisionTreeClassifier(
        min_samples_leaf=min_leaf,
        random_state=42
    )

    clf.fit(X, y, sample_weight=weights)

    print(f"\nCombined tree trained:")
    print(f"  min_samples_leaf: {min_leaf}")
    print(f"  Depth: {clf.tree_.max_depth}")
    print(f"  Leaves: {clf.tree_.n_leaves}")
    print(f"  Nodes: {clf.tree_.node_count}")
    print(f"  Accuracy: {clf.score(X, y, sample_weight=weights):.2%}")

    # Feature importance
    print(f"\nTop 10 features by importance:")
    feature_importance = sorted(
        zip(feature_columns, clf.feature_importances_),
        key=lambda x: x[1],
        reverse=True
    )
    for i, (feat, importance) in enumerate(feature_importance[:10], 1):
        print(f"  {i}. {feat}: {importance:.4f}")

    return clf, feature_columns


def export_tree_to_mermaid(clf: DecisionTreeClassifier, feature_columns: List[str],
                           actions: List[str], output_path: str):
    """
    Export combined tree to Mermaid file

    Args:
        clf: Trained classifier
        feature_columns: List of feature names (including nolead)
        actions: List of actions (classes)
        output_path: Path to save .mmd file
    """
    # Generate Mermaid diagram
    mermaid_lines = ['flowchart TD']
    mermaid_lines.extend(tree_to_mermaid(
        clf.tree_,
        feature_columns,
        sorted(actions),
        include_styles=False
    ))

    mermaid_content = '\n'.join(mermaid_lines)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(mermaid_content)

    print(f"\nMermaid diagram saved: {output_path}")
    print(f"  Size: {len(mermaid_content)} characters")


def export_tree_metadata(clf: DecisionTreeClassifier, feature_columns: List[str],
                        actions: List[str], board: str, min_leaf: int, output_path: str):
    """
    Export combined tree metadata to JSON

    Args:
        clf: Trained classifier
        feature_columns: List of feature names (including nolead)
        actions: List of actions
        board: Board string
        min_leaf: min_samples_leaf parameter
        output_path: Path to save JSON file
    """
    tree = clf.tree_

    # Feature importance
    feature_importance = {}
    for i, feat in enumerate(feature_columns):
        importance = clf.feature_importances_[i]
        if importance > 0:
            feature_importance[feat] = round(float(importance), 4)

    # Sort by importance
    feature_importance = dict(sorted(feature_importance.items(),
                                    key=lambda x: x[1], reverse=True))

    # Metadata
    metadata = {
        'tree_type': 'combined',
        'board': board,
        'min_samples_leaf': min_leaf,
        'features': len(feature_columns),
        'tree_stats': {
            'max_depth': int(tree.max_depth),
            'n_leaves': int(tree.n_leaves),
            'n_nodes': int(tree.node_count),
            'n_features_used': len([f for f in feature_columns if clf.feature_importances_[feature_columns.index(f)] > 0])
        },
        'actions': sorted(actions),
        'feature_importance': feature_importance
    }

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Metadata saved: {output_path}")
    print(f"  Features used: {metadata['tree_stats']['n_features_used']}")
    print(f"  Top 3 features: {list(feature_importance.keys())[:3]}")


def main():
    """Main function to build combined tree"""

    # Board
    board = '9s6d5c'

    print("=" * 60)
    print("Building Combined Decision Tree (Lead + NoLead)")
    print("=" * 60)
    print(f"\nBoard: {board}")
    print()

    # Create output folder
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Lead range files
    range_files_lead = {
        'bet_1/2pot': '/mnt/c/JN/test ranges/9s6d5c/1_2 POT.csv',
        'check': '/mnt/c/JN/test ranges/9s6d5c/CHECK.csv'
    }

    # NoLead range files
    range_files_nolead = {
        'bet_1/2pot': '/mnt/c/JN/test ranges/9s6d5c/NoLead_1_2 POT.csv',
        'check': '/mnt/c/JN/test ranges/9s6d5c/NoLead_CHECK.csv'
    }

    # Combine all ranges
    df_combined = combine_all_ranges(range_files_lead, range_files_nolead, board)

    # Build matrix
    df_matrix, actions = build_combined_matrix(df_combined)

    # Save combined matrix
    matrix_file = output_dir / 'bucket_matrix_combined_9s6d5c.csv'
    df_matrix.to_csv(matrix_file, index=False)
    print(f"\nCombined matrix saved: {matrix_file}")

    # Build trees with different min_leaf
    for min_leaf in [1, 10, 50]:
        print(f"\n" + "=" * 60)
        print(f"Building tree with min_leaf = {min_leaf}")
        print("=" * 60)

        clf, features = build_decision_tree(df_matrix, actions, min_leaf=min_leaf)

        # Export to Mermaid
        mermaid_file = output_dir / f'tree_combined_9s6d5c_min{min_leaf}.mmd'
        export_tree_to_mermaid(clf, features, actions, str(mermaid_file))

        # Export metadata
        json_file = output_dir / f'tree_combined_9s6d5c_min{min_leaf}_metadata.json'
        export_tree_metadata(clf, features, actions, board, min_leaf, str(json_file))

    # Final statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"\nBoard: {board}")
    print(f"\nCombined Matrix:")
    print(f"  Feature combinations: {len(df_matrix)}")
    print(f"  Features: 86 (nolead + 85 buckets)")
    print(f"  Actions: {actions}")
    print(f"\nAll files saved in: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
