import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
from typing import Dict, List, Tuple
import uuid

# Configure page
st.set_page_config(
    page_title="ExpenseSplit - Splitwise Clone",
    page_icon="💰",
    layout="wide"
)

class ExpenseSplitter:
    def __init__(self):
        self.data_file = "expense_data.json"
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    st.session_state.expenses = data.get('expenses', [])
                    st.session_state.groups = data.get('groups', {})
                    st.session_state.members = set(data.get('members', []))
            else:
                # Initialize with empty data if file doesn't exist
                st.session_state.expenses = []
                st.session_state.groups = {}
                st.session_state.members = set()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            # Initialize with empty data on error
            st.session_state.expenses = []
            st.session_state.groups = {}
            st.session_state.members = set()
        
        self.expenses = st.session_state.expenses
        self.groups = st.session_state.groups
        self.members = st.session_state.members
    
    def save_data(self):
        """Save data to JSON file"""
        try:
            data = {
                'expenses': self.expenses,
                'groups': self.groups,
                'members': list(self.members)
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            st.error(f"Error saving data: {e}")
    
    def add_expense(self, description: str, amount: float, paid_by: List[str], 
                   paid_amounts: Dict[str, float], split_among: List[str], 
                   split_type: str = "equal", custom_splits: Dict[str, float] = None, 
                   ratio_splits: Dict[str, float] = None, group: str = "General"):
        """Add a new expense with multiple payers support"""
        expense_id = str(uuid.uuid4())
        
        # Calculate splits
        if split_type == "equal":
            split_amount = amount / len(split_among)
            splits = {member: split_amount for member in split_among}
        elif split_type == "custom" and custom_splits:
            splits = custom_splits
        elif split_type == "ratio" and ratio_splits:
            # Calculate ratio-based splits
            total_ratio = sum(ratio_splits.values())
            splits = {member: (ratio_splits[member] / total_ratio) * amount 
                     for member in split_among if member in ratio_splits}
        else:
            splits = {member: 0 for member in split_among}
        
        expense = {
            'id': expense_id,
            'description': description,
            'amount': amount,
            'paid_by': paid_by,
            'paid_amounts': paid_amounts,
            'split_among': split_among,
            'splits': splits,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'group': group
        }
        
        self.expenses.append(expense)
        st.session_state.expenses = self.expenses
        self.save_data()  # Save after adding
        return expense_id
    
    def delete_expense(self, expense_id: str):
        """Delete an expense"""
        self.expenses = [exp for exp in self.expenses if exp['id'] != expense_id]
        st.session_state.expenses = self.expenses
        self.save_data()  # Save after deleting
    
    def add_member(self, member_name: str):
        """Add a new member"""
        if member_name and member_name not in self.members:
            self.members.add(member_name)
            st.session_state.members = self.members
            self.save_data()  # Save after adding member
            return True
        return False
    
    def remove_member(self, member_name: str):
        """Remove a member"""
        if member_name in self.members:
            self.members.remove(member_name)
            st.session_state.members = self.members
            self.save_data()  # Save after removing member
            return True
        return False
    
    def calculate_balances(self, group_filter: str = None) -> Dict[str, float]:
        """Calculate who owes whom with multiple payers support"""
        balances = {}
        
        # Filter expenses by group if specified
        expenses_to_process = self.expenses
        if group_filter and group_filter != "All Groups":
            expenses_to_process = [exp for exp in self.expenses if exp['group'] == group_filter]
        
        # Initialize balances for all members
        for member in self.members:
            balances[member] = 0.0
        
        # Process each expense
        for expense in expenses_to_process:
            # Add the amounts paid by each payer
            for payer, amount_paid in expense['paid_amounts'].items():
                if payer in balances:
                    balances[payer] += amount_paid
            
            # Subtract each person's share
            for member, share in expense['splits'].items():
                if member in balances:
                    balances[member] -= share
        
        return balances
    
    def get_settlements(self, group_filter: str = None) -> List[Dict]:
        """Calculate minimum settlements needed"""
        balances = self.calculate_balances(group_filter)
        
        # Separate creditors and debtors
        creditors = {k: v for k, v in balances.items() if v > 0.01}
        debtors = {k: abs(v) for k, v in balances.items() if v < -0.01}
        
        settlements = []
        
        # Calculate settlements
        for debtor, debt_amount in debtors.items():
            remaining_debt = debt_amount
            
            for creditor, credit_amount in list(creditors.items()):
                if remaining_debt <= 0.01:
                    break
                
                if credit_amount > 0.01:
                    settlement_amount = min(remaining_debt, credit_amount)
                    
                    settlements.append({
                        'from': debtor,
                        'to': creditor,
                        'amount': settlement_amount
                    })
                    
                    remaining_debt -= settlement_amount
                    creditors[creditor] -= settlement_amount
        
        return settlements
    
    def add_group(self, group_name: str, members: List[str]):
        """Add a new group"""
        if group_name not in self.groups:
            self.groups[group_name] = members
            st.session_state.groups = self.groups
            self.save_data()  # Save after adding group
            return True
        return False
    
    def get_group_expenses(self, group_name: str) -> List[Dict]:
        """Get expenses for a specific group"""
        return [exp for exp in self.expenses if exp['group'] == group_name]
    
    def export_data(self):
        """Export data as JSON string for backup"""
        data = {
            'expenses': self.expenses,
            'groups': self.groups,
            'members': list(self.members),
            'export_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return json.dumps(data, indent=2)
    
    def import_data(self, json_data: str):
        """Import data from JSON string"""
        try:
            data = json.loads(json_data)
            
            # Validate data structure
            if 'expenses' in data and 'members' in data:
                st.session_state.expenses = data.get('expenses', [])
                st.session_state.groups = data.get('groups', {})
                st.session_state.members = set(data.get('members', []))
                
                # Update instance variables
                self.expenses = st.session_state.expenses
                self.groups = st.session_state.groups
                self.members = st.session_state.members
                
                # Save the imported data
                self.save_data()
                return True
            else:
                st.error("Invalid data format")
                return False
        except json.JSONDecodeError:
            st.error("Invalid JSON format")
            return False
        except Exception as e:
            st.error(f"Error importing data: {e}")
            return False

def main():
    st.title("💰 ExpenseSplit")
    st.markdown("*Your personal expense tracking solution with persistent data storage*")
    
    # Initialize the expense splitter
    splitter = ExpenseSplitter()
    
    # ========== SECTION 1: MEMBER MANAGEMENT ==========
    with st.expander("👥 Manage Members", expanded=len(st.session_state.members) < 2):
        col1, col2 = st.columns([2, 1])
        with col1:
            new_member = st.text_input("Add member", placeholder="Enter name", key="add_member_input")
        with col2:
            if st.button("Add", key="add_member_btn"):
                if splitter.add_member(new_member):
                    st.success(f"Added {new_member}")
                    st.rerun()
                elif new_member:
                    st.warning(f"{new_member} already exists")
        
        if st.session_state.members:
            st.write("**Current members:**")
            cols = st.columns(min(len(st.session_state.members), 4))
            for i, member in enumerate(st.session_state.members):
                with cols[i % 4]:
                    if st.button(f"❌ {member}", key=f"remove_{member}"):
                        splitter.remove_member(member)
                        st.rerun()
    
    # ========== SECTION 2: DATA MANAGEMENT ==========
    with st.expander("💾 Data Management"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📤 Export Data**")
            if st.button("Export to JSON", key="export_btn"):
                export_data = splitter.export_data()
                st.download_button(
                    label="📥 Download Backup",
                    data=export_data,
                    file_name=f"expense_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            st.markdown("**📥 Import Data**")
            uploaded_file = st.file_uploader("Choose JSON file", type=['json'])
            if uploaded_file is not None:
                try:
                    json_data = uploaded_file.read().decode('utf-8')
                    if st.button("Import Data", key="import_btn"):
                        if splitter.import_data(json_data):
                            st.success("Data imported successfully!")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error reading file: {e}")
    
    # ========== SECTION 3: ADD EXPENSE ==========
    st.markdown("---")
    st.markdown("### ➕ Add New Expense")
    
    if len(st.session_state.members) < 2:
        st.info("👆 Add at least 2 members to start splitting expenses")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            description = st.text_input("💬 Description", placeholder="e.g., Dinner at restaurant")
            amount = st.number_input("💵 Total Amount", min_value=0.01, step=0.01, format="%.2f")
            
            # Group selection
            group_options = ["General"] + list(st.session_state.groups.keys())
            selected_group = st.selectbox("📁 Group", group_options)
        
        with col2:
            # Multiple payers section
            st.markdown("**💳 Who paid?**")
            payers = st.multiselect("Select payers", list(st.session_state.members), key="payers")
            
            paid_amounts = {}
            if payers:
                if len(payers) == 1:
                    # Single payer - they paid the full amount
                    paid_amounts[payers[0]] = amount
                    st.info(f"{payers[0]} paid the full amount: ${amount:.2f}")
                else:
                    # Multiple payers - specify amounts
                    st.markdown("**Specify amounts paid by each person:**")
                    total_paid = 0
                    for payer in payers:
                        paid_amount = st.number_input(f"Amount paid by {payer}", 
                                                    min_value=0.0, step=0.01, 
                                                    key=f"paid_by_{payer}")
                        paid_amounts[payer] = paid_amount
                        total_paid += paid_amount
                    
                    # Show total and validation
                    if total_paid > 0:
                        st.write(f"**Total paid:** ${total_paid:.2f}")
                        if abs(total_paid - amount) > 0.01:
                            st.warning(f"⚠️ Total paid (${total_paid:.2f}) doesn't match expense amount (${amount:.2f})")
        
        # Split section
        st.markdown("**🔄 How to split?**")
        
        split_type = st.radio("Split type", ["Equal", "Custom", "Ratio"], horizontal=True)
        
        if split_type == "Equal":
            split_among = st.multiselect("Split equally among", list(st.session_state.members), 
                                       default=list(st.session_state.members))
            
            if split_among:
                split_amount = amount / len(split_among)
                st.info(f"Each person owes: ${split_amount:.2f}")
        
        elif split_type == "Custom":
            split_among = st.multiselect("Split among", list(st.session_state.members))
            
            custom_splits = {}
            if split_among:
                st.markdown("**Specify custom amounts:**")
                cols = st.columns(min(len(split_among), 3))
                total_custom = 0
                
                for i, member in enumerate(split_among):
                    with cols[i % 3]:
                        custom_amount = st.number_input(f"{member}", 
                                                      min_value=0.0, step=0.01, 
                                                      key=f"custom_{member}")
                        custom_splits[member] = custom_amount
                        total_custom += custom_amount
                
                st.write(f"**Total custom split:** ${total_custom:.2f}")
                if abs(total_custom - amount) > 0.01:
                    st.warning(f"⚠️ Custom split (${total_custom:.2f}) doesn't match expense amount (${amount:.2f})")
        
        elif split_type == "Ratio":
            split_among = st.multiselect("Split among", list(st.session_state.members))
            
            ratio_splits = {}
            if split_among:
                st.markdown("**Specify ratio for each person/family:**")
                st.info("💡 **Tip**: Enter ratios like 5, 3, 2 for families of different sizes, or 1, 1, 1 for equal parts")
                
                cols = st.columns(min(len(split_among), 3))
                total_ratio = 0
                
                for i, member in enumerate(split_among):
                    with cols[i % 3]:
                        ratio_value = st.number_input(f"{member} (ratio)", 
                                                    min_value=0.1, step=0.1, 
                                                    value=1.0,
                                                    key=f"ratio_{member}")
                        ratio_splits[member] = ratio_value
                        total_ratio += ratio_value
                
                if total_ratio > 0:
                    st.markdown("**📊 Ratio breakdown:**")
                    ratio_cols = st.columns(min(len(split_among), 3))
                    for i, (member, ratio) in enumerate(ratio_splits.items()):
                        with ratio_cols[i % 3]:
                            percentage = (ratio / total_ratio) * 100
                            member_amount = (ratio / total_ratio) * amount
                            st.write(f"**{member}**: {ratio}/{total_ratio} = {percentage:.1f}% = ${member_amount:.2f}")
                    
                    # Show ratio in simplified form
                    st.info(f"💡 **Final ratio**: {' : '.join([f'{v:.1f}' for v in ratio_splits.values()])}")
        
        # Add expense button
        can_add_expense = (
            description and 
            amount > 0 and 
            payers and 
            split_among and
            (split_type == "Equal" or 
             (split_type == "Custom" and abs(sum(custom_splits.values()) - amount) < 0.01) or
             (split_type == "Ratio" and ratio_splits)) and
            (len(payers) == 1 or abs(sum(paid_amounts.values()) - amount) < 0.01)
        )
        
        if st.button("✅ Add Expense", type="primary", disabled=not can_add_expense, use_container_width=True):
            # Prepare the expense data
            final_custom_splits = custom_splits if split_type == "Custom" else None
            final_ratio_splits = ratio_splits if split_type == "Ratio" else None
            
            expense_id = splitter.add_expense(
                description=description,
                amount=amount,
                paid_by=payers,
                paid_amounts=paid_amounts,
                split_among=split_among,
                split_type=split_type.lower(),
                custom_splits=final_custom_splits,
                ratio_splits=final_ratio_splits,
                group=selected_group
            )
            
            st.success("🎉 Expense added successfully!")
            st.balloons()
            st.rerun()
    
    # ========== SECTION 4: CURRENT BALANCES ==========
    if splitter.expenses:
        st.markdown("---")
        st.markdown("### 💳 Current Balances")
        
        # Group filter for balances
        group_options = ["All Groups"] + list(set([exp['group'] for exp in splitter.expenses]))
        selected_group_filter = st.selectbox("Filter by group", group_options, key="balance_filter")
        
        # Calculate balances
        balances = splitter.calculate_balances(selected_group_filter)
        settlements = splitter.get_settlements(selected_group_filter)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**💰 Who owes/receives money:**")
            for member, balance in balances.items():
                if balance > 0.01:
                    st.success(f"✅ {member}: +${balance:.2f} (should receive)")
                elif balance < -0.01:
                    st.error(f"💸 {member}: ${balance:.2f} (owes money)")
                else:
                    st.info(f"⚖️ {member}: ${balance:.2f} (all settled)")
        
        with col2:
            st.markdown("**🔄 Suggested settlements:**")
            if settlements:
                for settlement in settlements:
                    st.write(f"💸 **{settlement['from']}** → **{settlement['to']}**: ${settlement['amount']:.2f}")
            else:
                st.success("🎉 Everyone is settled up!")
        
        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            total_expenses = sum(exp['amount'] for exp in splitter.expenses)
            st.metric("Total Expenses", f"${total_expenses:.2f}")
        with col2:
            st.metric("Number of Expenses", len(splitter.expenses))
        with col3:
            st.metric("Active Members", len(st.session_state.members))
    
    # ========== SECTION 5: VIEW ALL EXPENSES ==========
    if splitter.expenses:
        st.markdown("---")
        st.markdown("### 📋 All Expenses")
        
        # Group filter for expenses
        group_options = ["All Groups"] + list(set([exp['group'] for exp in splitter.expenses]))
        selected_expense_filter = st.selectbox("Filter expenses by group", group_options, key="expense_filter")
        
        # Filter expenses
        filtered_expenses = splitter.expenses
        if selected_expense_filter != "All Groups":
            filtered_expenses = [exp for exp in splitter.expenses if exp['group'] == selected_expense_filter]
        
        # Display expenses
        for expense in reversed(filtered_expenses):
            with st.expander(f"💵 {expense['description']} - ${expense['amount']:.2f} ({expense['date'][:10]})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**💳 Paid by:**")
                    for payer, amount_paid in expense['paid_amounts'].items():
                        st.write(f"• {payer}: ${amount_paid:.2f}")
                    st.write(f"**📁 Group:** {expense['group']}")
                
                with col2:
                    st.write("**🔄 Split details:**")
                    for member, amount_split in expense['splits'].items():
                        st.write(f"• {member}: ${amount_split:.2f}")
                    
                    # Show split type for better understanding
                    if 'ratio_splits' in expense and expense.get('ratio_splits'):
                        st.write("**📊 Split type:** Ratio")
                        ratio_display = " : ".join([f"{v:.1f}" for v in expense['ratio_splits'].values()])
                        st.write(f"**Ratio:** {ratio_display}")
                    elif expense['split_type'] == 'custom':
                        st.write("**📊 Split type:** Custom amounts")
                    else:
                        st.write("**📊 Split type:** Equal split")
                
                with col3:
                    if st.button(f"🗑️ Delete", key=f"delete_{expense['id']}", type="secondary"):
                        splitter.delete_expense(expense['id'])
                        st.success("Expense deleted!")
                        st.rerun()
    
    # ========== SECTION 6: CLEAR ALL DATA ==========
    if splitter.expenses or splitter.members:
        st.markdown("---")
        with st.expander("🗑️ Danger Zone"):
            st.warning("⚠️ **Warning:** This will permanently delete all your data!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Expenses", type="secondary"):
                    st.session_state.expenses = []
                    splitter.expenses = []
                    splitter.save_data()
                    st.success("All expenses cleared!")
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear All Data", type="secondary"):
                    st.session_state.expenses = []
                    st.session_state.members = set()
                    st.session_state.groups = {}
                    splitter.expenses = []
                    splitter.members = set()
                    splitter.groups = {}
                    splitter.save_data()
                    st.success("All data cleared!")
                    st.rerun()
    
    # ========== FOOTER ==========
    st.markdown("---")
    st.markdown("💡 **ExpenseSplit** - Your personal expense tracking solution with persistent data storage")
    st.markdown("📁 *Data is automatically saved to expense_data.json*")

if __name__ == "__main__":
    main()